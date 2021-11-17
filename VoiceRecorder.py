import functools

import sounddevice
from scipy.io import wavfile


def record_modify(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("Recording started")
        r = func(*args, **kwargs)
        print("Recording complete")
        wavfile.write("rec.wav", kwargs['fs'], r)
        print("Record saved")

    return wrapper


@record_modify
def recorder(sec, fs):
    record = sounddevice.rec(int(fs * sec), samplerate=fs, channels=2)
    sounddevice.wait()
    return record


if __name__ == "__main__":
    recorder(5, 16000)
