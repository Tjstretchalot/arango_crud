"""Test helper"""
import os


TEST_CLUSTER_URLS = os.env['TEST_ARANGO_CLUSTER_URLS'].split(',')
TEST_ARANGO_DB = os.env['TEST_ARANGO_DB']
TEST_USERNAME = os.env['TEST_ARANGO_USERNAME']
TEST_PASSWORD = os.env.get('TEST_ARANGO_PASSWORD', '')
