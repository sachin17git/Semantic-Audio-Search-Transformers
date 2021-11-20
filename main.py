# This program is based on NLP. Uses AWS services.
import os
import pathlib
import boto3
import torch
from PyPDF2 import PdfFileReader
from collections import namedtuple
from sentence_transformers import SentenceTransformer, util
from transformers.pipelines import pipeline

import AwsOperations
import VoiceRecorder

VoiceConfig = namedtuple("VoiceConfig", "seconds fs")
v_config = VoiceConfig(5, 16000)

s3 = boto3.client('s3')
transcribe = boto3.client("transcribe", region_name="us-east-2")

aws_op = AwsOperations.AwsOp(s3, transcribe)


def aws_rec_start(fname):
    VoiceRecorder.recorder(sec=v_config.seconds, fs=v_config.fs)
    aws_op.upload_audio_s3(filename=fname)
    q = aws_op.transcribe_job(filename=os.path.basename(fname))
    return q


def aws_rec_clean_up(fname):
    aws_op.delete_audio_s3(os.path.basename(fname).split(".")[0])
    aws_op.delete_job("S2T")


def model_loader():
    print("Loading models.")
    emb = SentenceTransformer('all-MiniLM-L6-v2')
    model_name = "phiyodr/bart-large-finetuned-squad2"
    print("All models loaded.")
    nlp = pipeline('question-answering', model=model_name, tokenizer=model_name)
    print("Pipeline created.")
    return emb, nlp


def read_create_corpus(file_name):
    corpus_temp = []
    if pathlib.Path(file_name).suffix == ".pdf":
        txt_from_pdf = []
        sent_adder = lambda x: x.replace("\n", "").strip()
        reader = PdfFileReader(file_name)
        n_pages = reader.getNumPages()
        print(f"File format : PDF\nPages detected: {n_pages}")

        for p in range(n_pages):
            page = reader.getPage(p)
            pdf_text_page = page.extractText()
            txt_from_pdf.append(pdf_text_page.strip())

        for para in txt_from_pdf:
            sent = para.split(".")
            sent = [s.strip() for s in sent if s.__len__() > 5]
            corpus_temp = corpus_temp + list(map(sent_adder, sent))

    elif pathlib.Path(file_name).suffix == ".txt":
        sent_adder = lambda x: x.strip()
        with open(file_name, 'r', encoding='utf-8') as file:
            data = file.readlines()
            data = [d.strip() for d in data]

        for para in data:
            sent = para.split(".")
            sent = [s.strip() for s in sent if s.__len__() > 5]
            corpus_temp = corpus_temp + list(map(sent_adder, sent))

    return corpus_temp


def search(qs, top):
    text = []
    for qry in qs:
        query_embedding = embedder.encode(qry, convert_to_tensor=True)
        cos_scores = util.pytorch_cos_sim(query_embedding, corpus_embeddings)[0]
        top_results = torch.topk(cos_scores, k=top)
        for score, idx in zip(top_results[0], top_results[1]):
            text.append(corpus[idx])
        con = '. '.join(text)
        return con


def qa(question, e_context, nlp):
    inputs = {
        'question': question,
        'context': e_context
    }
    return nlp(inputs)


if __name__ == "__main__":
    file_inp = str(input("Enter the file name: "))
    filename_document = os.path.join(os.getcwd(), file_inp)
    try:
        corpus = read_create_corpus(filename_document)
    except FileNotFoundError as e:
        print(e)
        exit(1)
    embedder, NLP = model_loader()
    print("Corpus (number of sentences) :", corpus.__len__())
    corpus_embeddings = embedder.encode(corpus, convert_to_tensor=True)
    top_k = min(5, len(corpus))
    filename = os.path.join(os.getcwd(), "rec.wav")
    print("Please speak (search query) : ")
    inp = 'Y'

    while inp not in ["N", "n"]:
        query = aws_rec_start(filename)
        print("\n")
        queries = [query.strip()]
        context = search(queries, top_k)
        result = qa(queries[0], context, NLP)
        print("Search query :", queries[0])
        print(f"Result : {result['answer']}")
        print(f"Context:\n")
        print(context)
        print("\n")
        aws_rec_clean_up(filename)
        inp = str(input("Continue searching? [Y/N]: "))
    print("Done")
