import os
import time

import pandas as pd


class AwsOp:
    def __init__(self, s3, transcribe):
        self.s3 = s3
        self.transcribe = transcribe

    def list_buckets_s3(self):
        response = self.s3.list_buckets()
        for buck in response['Buckets']:
            print(buck['Name'])

    def upload_audio_s3(self, filename):
        with open(filename, "rb") as file:
            self.s3.upload_fileobj(file, "aws-audio", os.path.basename(filename).split(".")[0])

    def delete_audio_s3(self, filename):
        self.s3.delete_object(Bucket="aws-audio", Key=os.path.basename(filename).split(".")[0])

    def transcribe_job(self, filename):
        job_name = "S2T"
        job_uri = os.path.join("s3://aws-audio/", filename.split(".")[0])
        print(job_uri)
        self.transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat="wav",
            LanguageCode="en-US"
        )
        while True:
            status = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            print("Not ready yet...")
            time.sleep(5)

        results = pd.read_json(status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"])
        return results["results"]["transcripts"][0]["transcript"]

    def delete_job(self, job_name):
        self.transcribe.delete_transcription_job(TranscriptionJobName=job_name)


if __name__ == "__main__":
    """
    path = os.getcwd()
    file_path = os.path.join(path, "rec.wav")
    upload_audio_s3(file_path)
    speech_to_txt = transcribe_job(os.path.basename(file_path))
    print(speech_to_txt)
    delete_audio_s3(os.path.basename(file_path).split(".")[0])"""

