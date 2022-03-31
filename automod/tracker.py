"""
tracker.py
"""
import logging
import json
import datetime

import pytz
import boto3

from .clubhouse import Config


class Tracker:
    S3_BUCKET = Config.config_to_dict(Config.load_config(), "S3", "bucket")

    def s3_client_dump(self, dump, key):
        """
        A function to set the interval decorator.

        :param dump: The server data to be dumped
        :type dump: any
        :param key: A label for the dump file
        :type key: str
        :return: Server response
        :rtype: bool
        """
        if isinstance(dump, dict):
            dump = json.dumps(dump)
        s3_client = boto3.client("s3")
        bucket = self.S3_BUCKET
        timestamp = datetime.now(pytz.timezone('UTC')).isoformat()
        key = f"{key}_{timestamp}.json"
        run = s3_client.put_object(
            Body=dump,
            Bucket=bucket,
            Key=key,
        )
        response = run.get("success")
        logging.info(run)
        return response

    def data_dump(self, dump, source, channel=""):
        log = f"Dumped {source} {channel}"
        if source == "feed":
            key = source
        elif source == "channel":
            key = f"channel_{dump.get('channel')}"
        elif source == "channel_dict":
            key = f"channel_{dump.get('channel_info').get('channel')}"
        elif source == 'join':
            key = f"join_{dump.get('channel')}"
        else:
            key = "unrecognized"
            log = f"Unrecognized dumping source {source}"
        logging.info(log)
        response = self.s3_client_dump(dump, key)
        return response
