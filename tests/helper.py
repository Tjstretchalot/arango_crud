"""Test helper"""
import os


TEST_CLUSTER_URLS = os.environ['TEST_ARANGO_CLUSTER_URLS'].split(',')
TEST_ARANGO_DB = os.environ['TEST_ARANGO_DB']
TEST_USERNAME = os.environ['TEST_ARANGO_USERNAME']
TEST_PASSWORD = os.environ.get('TEST_ARANGO_PASSWORD', '')
