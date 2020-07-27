#!/usr/bin/env python3
"""
Prepares a MIDI file for reproducing transients from Spear-analysis files on a hardware or software synth.
Spear text partials export format:
index   points  start   end
time    frequency   amplitude   [time   frequency   amplitude] ...
"""

__author__ = "Are Johansen Ormberg"
__version__ = "0.0.1"
__license__ = "CC"

from math import log, floor, ceil, trunc
from mido import MidiFile, MidiTrack, Message
from traces import TimeSeries

class Partial:
    "Individual partial with properties exported from Spear"
    
    freq_ts = TimeSeries()
    freq_vector = []
    amp_ts = TimeSeries()
    amp_vector = []
    start = 0
    end = 0
    length = 0
    index = 0
    root_frequency = 440
    pb_range = 4
    note_list = MidiTrack()
    offset = 0
    
    def __init__(self, index, length, start, end, time_vector, freq_vector, amp_vector, root_frequency, pb_range, offset):
        self.offset = int(offset*1000)
        self.index = index
        self.length = length
        self.start = int(start*1000) #+self.offset
        self.end = int(end*1000) #+self.offset
        freq_vector = list(map(lambda x: float(x.replace(',','.')), freq_vector))
        self.time_vector = list(map(lambda x: floor(float(x.replace(',','.'))*1000)+self.offset, time_vector))
        amp_vector = list(map(lambda x: float(x.replace(',','.')), amp_vector))
        
        #redestribute irregular time data
        for k,t in enumerate(self.time_vector):
            self.freq_ts[t] = (freq_vector[k])
            self.amp_ts[t] = (amp_vector[k])
        self.freq_ts = self.freq_ts.sample(sampling_period=1,start=self.start,end=self.end,interpolate='linear')
        self.amp_ts = self.amp_ts.sample(sampling_period=1,start=self.start,end=self.end,interpolate='linear')
        self.freq_vector = [x[1] for x in self.freq_ts]
        self.amp_vector = [x[1] for x in self.amp_ts]
        self.root_frequency = root_frequency
        self.pb_range = pb_range
        print("index"+index)
        self.build_note_list(self.start, self.end)

    def build_note_list(self, start, end):
        if len(self.freq_vector[start:end]) == 0: return
        distance = midi_note_distance(max(self.freq_vector[start:end]),min(self.freq_vector[start:end]),self.root_frequency)
        if distance < (self.pb_range*2):
            midi_note = floor(f2st(min(self.freq_vector[start:end]), self.root_frequency) + 69 + (self.pb_range/2))
            if midi_note < 0 or midi_note > 127: return
            self.note_list.append(Message('note_on', note=midi_note, velocity=64, time=0))
            print(self.note_list[-1])
            for i, f in enumerate(self.freq_vector[start:end]):
                bend = frequency_to_pitchbend(f, midi_note, self.root_frequency, self.pb_range)
                self.note_list.append(Message('pitchwheel', pitch=bend, time=1))
                print(self.note_list[-1])
            self.note_list.append(Message('note_off', note=midi_note, velocity=64, time=0))
            print(self.note_list[-1])
        else:
            middle = trunc(len(self.freq_vector[start:end])/2)
            self.build_note_list(start, middle)
            self.build_note_list(middle, end)


def midi_note_distance(fmax,fmin,root_frequency):
    return ceil(f2st(fmax, root_frequency)) - floor(f2st(fmin, root_frequency))

def f2st(hz, base=440):
    "Frequency to semitones function. Adapted from https://rdrr.io/cran/hqmisc/man/f2st.html"
    semi1 = log(2)/12
    return((log(hz) - log(base))/semi1)

def frequency_to_pitchbend(frequency, midi_note, root_frequency, pb_range):
    return floor((percentage(f2st(frequency) + 69, midi_note - pb_range, midi_note + pb_range) * 16382)-8191)

def percentage(x,a,b):
    return (x-a)/(b-a)
    
def midi_note_to_frequency(midi_note, root_frequency):
    return (root_frequency / 32) * (2 ** ((midi_note - 9) / 12))
    
def pairwise(iterable):
    "from https://stackoverflow.com/a/5389547"
    a = iter(iterable)
    return zip(a, a)
    
def main():
    #open spear file
    with open('seinfeld slap.txt') as f:
        spear = f.readlines()
    
    root_frequency = 440
    pb_range = 4
    offset = 0

    #init midi file
    mid = MidiFile()
    tracks = MidiTrack()
    
    #read data from spear file
    for a,b in pairwise(spear[4:]):
        a_split = a.split(' ')
        b_split = b.split(' ')
        partial = (
            Partial(a_split[0].replace(',','.'), 
                float(a_split[1].replace(',','.')), 
                float(a_split[2].replace(',','.')), 
                float(a_split[3].replace(',','.')), 
                b_split[0::3], 
                b_split[1::3], 
                b_split[2::3], 
                root_frequency, 
                pb_range,
                offset
            )
        )
        
        offset += float(a_split[3].replace(',','.'))
        
        if(partial.note_list): 
            tracks.extend(partial.note_list)

    mid.tracks.append(tracks)

    print('Saving output.mid')
    mid.save('output.mid')

if __name__ == "__main__":
    main()
   