import struct
import numpy as np
import os
import re
import datetime
from annotations import open_json
import logging


def open_project(path):
    """
        Given a directory path, open_project opens each .wav file as a numpy array,
        stacks all of them into a single numpy array and returns it as the first element in result,
        the timestamp as a datetime object as the second element in result
        and a list of Annotation objects  as the third element in result if a json file is present,
        else it returns an empty list.
    """
    logging.info('Opening project at path: {}'.format(path))
    contents = os.listdir(path)
    calfile = ""
    datafiles = []
    jsonfile = ""
    # acquire filepaths for the different project files
    for filepath in contents:
        if re.match(
                r'\d{2}-\d{2}-\d{4}_\d{2}_\d{2}_\d{2}_\d{1,4}_\d*.cal', filepath):
            logging.info('Found calfile: {}'.format(filepath))
            calfile = path + filepath
        elif re.match(r'\d{2}-\d{2}-\d{4}_\d{2}_\d{2}_\d{2}_\d{1,4}_\d*.wav', filepath):
            logging.info('Found datafile: {}'.format(filepath))
            datafiles.append(path + filepath)
        elif re.match(r'.*\.json', filepath):
            logging.info('Found jsonfile: {}'.format(filepath))
            jsonfile = path + filepath
    # sort datafiles to obtain the correct order of data
    datafiles.sort()
    raw_data = []

    logging.info('Creating numpy array from data')
    # create a numpy array from the datafiles
    for file in datafiles:
        try:
            tmp_data = read_wav(file)
        except Exception:
            logging.error('.wav file at {} could not be read'.format(file))
            raise Exception("One of the data files could not be read")
        raw_data.append(tmp_data)
    data = np.hstack(raw_data)
    data = data / 10

    # create timestamps
    logging.info('Creating timestamps')
    timestamps = None
    if calfile != "":
        try:
            logging.info('Getting initial timestamp')
            initial_time = get_initial_timestamp(calfile)
        except Exception:
            logging.info('.cal file at {} could not be read'.format(calfile))
            raise Exception("The .cal file could not be read")
        timestamps = np.arange(
            data.shape[0]) * datetime.timedelta(microseconds=1000 * 20)
        timestamps += initial_time
    # load annotations
    annotations = []
    if jsonfile != "":
        logging.info('Loading annotations')
        try:
            annotations = open_json(jsonfile)
        except Exception:
            logging.warning(
                'The annotations could not be loaded from file at {}'.format(jsonfile))
            annotations = [-1,
                           "The annotation file is in an incorrect format."]
    logging.info('Finished opening project')
    return data, timestamps, annotations


def check_valid_path(path):
    """
    Checks the path contents to see if it has .cal and .wav files and raises exceptions if it doesn't
    returns false if user clicked on cancel, or an unexpected scenario
    occurs for quiet handling
    """
    logging.info('Checking validity of path: {}'.format(path))
    contents = os.listdir(path)
    calfile = ""
    datafiles = []
    for filepath in contents:
        if re.match(
                r'\d{2}-\d{2}-\d{4}_\d{2}_\d{2}_\d{2}_\d{1,4}_\d*.cal', filepath):
            calfile = path + filepath
        elif re.match(r'\d{2}-\d{2}-\d{4}_\d{2}_\d{2}_\d{2}_\d{1,4}_\d*.wav', filepath):
            datafiles.append(path + filepath)
    if (calfile != "") and (datafiles != []):
        logging.info('Path valid.')
        return True
    elif calfile == "" and datafiles == [] and path == "/":
        logging.info('Cancel button was clicked')
        return False
    elif calfile == "" and datafiles == []:
        logging.error('Missing .cal and .wav files')
        raise Exception("Missing .cal file and .wav files")
    elif calfile == "":
        logging.error('Missing .cal file')
        raise Exception("Missing .cal file")
    elif datafiles == []:
        logging.error('Missing .wav file')
        raise Exception("Missing .wav files")
    return False


def read_wav(filename):
    """
        Reads a single wav file in the format of two bytes is equal to one ICB reading and returns it as a numpy array
    """
    logging.info('Reading .wav file at {}'.format(filename))
    frames = []
    with open(filename, 'rb') as infile:
        raw_data = infile.read(2)
        data = struct.unpack('h', raw_data)[0]
        while raw_data != b"":
            frames.append(data)
            raw_data = infile.read(2)
            if len(raw_data) == 2:
                data = struct.unpack('h', raw_data)[0]
    return np.array(frames)


def get_initial_timestamp(filename):
    """
        Reads a .cal file and returns the initial timestamp
    """
    logging.info('Reading .cal file at {}'.format(filename))
    timestamp = ""
    with open(filename, 'r') as infile:
        firstline = infile.readline()
        match = re.match(
            (r'(?P<timestamp>\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})'), firstline)
        timestamp = datetime.datetime.strptime(
            match.group(1), '%d-%m-%Y %H:%M:%S')
        return timestamp
