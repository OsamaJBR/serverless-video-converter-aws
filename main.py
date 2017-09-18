#!/usr/bin/python
import boto3
import urllib
import json
import os
import sys 
import random

# Configs
config = json.loads(open('./config.json').read())

# Clients
s3 = boto3.resource('s3')
transcoder = boto3.client('elastictranscoder', config['region_name'])

# Functions 
def get_pipeline_id():
    paginator = transcoder.get_paginator('list_pipelines')
    for page in paginator.paginate():
        for pipeline in page['Pipelines']:
            if pipeline['Name'] == random.choice(config['pipeline_name'][os.environ.get('env')]):
                return pipeline['Id']

def start_transcoding(in_fname,out_fname):
    for out in config['out_format']:
        try:
            transcoder.create_job(
                    PipelineId=get_pipeline_id(),
                    Input={
                        'Key': in_fname,
                        'FrameRate': 'auto',
                        'Resolution': 'auto',
                        'AspectRatio': 'auto',
                        'Interlaced': 'auto',
                        'Container': 'auto'
                    },
                    Outputs=[{
                        'Key': out_fname + out['ext'],
                        'PresetId': out['PresetId'],
                        'ThumbnailPattern' : "%s/thumbnails/%s.{count}" %(os.path.dirname(out_fname),os.path.basename(out_fname)+out['ext']),
                        'Rotate' : 'auto'
                    }]
                )
        except Exception as e:
            print(e)

def mark_media(key,state):
    # Do whatever you want to be done after converting the media
    return True

def lambda_handler(event,context):
    print(event)
    if not os.environ.get('env') :
        print("env variable should be added")
        exit()
    # This event could be fired by AWS S3 CreateObject Event, or by AWS Transcoder
    for record in event['Records']:
        if record.get('EventSource') == "aws:sns":
            # tell the api that the media is ready now ( or not).
            print("New SNS Notification was added to the topic : MESSAGE=%s" %record)
            return True
            media_converting_state = json.loads(record['Sns']['Message'])['state']
            if json.loads(record['Sns']['Message'])['state'] == 'COMPLETED':
                input_key = json.loads(record['Sns']['Message'])['input']['key']
                output_key = json.loads(record['Sns']['Message'])['outputs'][0]['key']
                mark_media(key,'ready')
        elif record.get('eventSource') == "aws:s3":
            filename = urllib.unquote_plus(record['s3']['object']['key'])
            fname, fext = os.path.splitext(filename)
            print("New job will be submitted for file=%s" %filename)
            job_ids = start_transcoding(in_fname=filename,out_fname=fname)
