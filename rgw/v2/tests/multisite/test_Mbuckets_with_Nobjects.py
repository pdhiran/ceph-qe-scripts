# test basic creation of buckets with objects
import os, sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../..")))
from v2.lib.resource_op import Config
import v2.lib.resource_op as s3lib
from v2.lib.s3.auth import Auth
import v2.utils.log as log
import v2.utils.utils as utils
from v2.utils.utils import HttpResponseParser
import traceback
import argparse
import yaml
import v2.lib.manage_data as manage_data
from v2.lib.exceptions import TestExecError
from v2.utils.test_desc import AddTestInfo
from v2.lib.s3.write_io_info import IOInfoInitialize, BasicIOInfoStructure
import time
import simplejson

TEST_DATA_PATH = None


def test_exec(config):
    test_info = AddTestInfo('create m buckets with n objects')
    try:
        test_info.started_info()
        # get user
        with open('user_details') as fout:
            all_users_info = simplejson.load(fout)
        for each_user in all_users_info:
            # authenticate
            auth = Auth(each_user)
            rgw_conn = auth.do_auth_using_client()
            rgw = auth.do_auth()
            bucket_list = []
            buckets = rgw_conn.list_buckets()
            log.info('buckets are %s' % buckets)
            for each_bucket in buckets['Buckets']:
                bucket_list.append(each_bucket['Name'])
            for bucket_name in bucket_list:
                # create 'bucket' resource object
                bucket = rgw.Bucket(bucket_name)
                log.info('In bucket: %s' % bucket_name)
                if config.test_ops['create_object'] is True:
                    # uploading data
                    log.info('s3 objects to create: %s' % config.objects_count)
                    for oc in range(config.objects_count):
                        s3_object_name = utils.gen_s3_object_name(bucket_name, oc)
                        log.info('s3 object name: %s' % s3_object_name)
                        s3_object_path = os.path.join(TEST_DATA_PATH, s3_object_name)
                        log.info('s3 object path: %s' % s3_object_path)
                        s3_object_size = utils.get_file_size(config.objects_size_range['min'],
                                                             config.objects_size_range['max'])
                        data_info = manage_data.io_generator(s3_object_path, s3_object_size)
                        if data_info is False:
                            TestExecError("data creation failed")
                        log.info('uploading s3 object: %s' % s3_object_path)
                        upload_info = dict({'access_key': each_user['access_key']}, **data_info)
                        #                                object_uploaded_status = bucket.upload_file(s3_object_path, s3_object_name)
                        object_uploaded_status = s3lib.resource_op({'obj': bucket,
                                                                    'resource': 'upload_file',
                                                                    'args': [s3_object_path, s3_object_name],
                                                                    'extra_info': upload_info})
                        if object_uploaded_status is False:
                            raise TestExecError("Resource execution failed: object upload failed")
                        if object_uploaded_status is None:
                            log.info('object uploaded')
                        if config.test_ops['download_object'] is True:
                            log.info('trying to download object: %s' % s3_object_name)
                            s3_object_download_name = s3_object_name + "." + "download"
                            s3_object_download_path = os.path.join(TEST_DATA_PATH, s3_object_download_name)
                            log.info('s3_object_download_path: %s' % s3_object_download_path)
                            log.info('downloading to filename: %s' % s3_object_download_name)
                            #                                    object_downloaded_status = bucket.download_file(s3_object_path, s3_object_name)
                            object_downloaded_status = s3lib.resource_op({'obj': bucket,
                                                                          'resource': 'download_file',
                                                                          'args': [s3_object_name,
                                                                                   s3_object_download_path],
                                                                          })
                            if object_downloaded_status is False:
                                raise TestExecError("Resource execution failed: object download failed")
                            if object_downloaded_status is None:
                                log.info('object downloaded')
                    if config.test_ops['delete_bucket_object'] is True:
                        log.info('listing all objects in bucket: %s' % bucket.name)
                        # objects = s3_ops.resource_op(bucket, 'objects', None)
                        objects = s3lib.resource_op({'obj': bucket,
                                                     'resource': 'objects',
                                                     'args': None})
                        log.info('objects :%s' % objects)
                        # all_objects = s3_ops.resource_op(objects, 'all')
                        all_objects = s3lib.resource_op({'obj': objects,
                                                         'resource': 'all',
                                                         'args': None})
                        log.info('all objects: %s' % all_objects)
                        for obj in all_objects:
                            log.info('object_name: %s' % obj.key)
                        log.info('deleting all objects in bucket')
                        # objects_deleted = s3_ops.resource_op(objects, 'delete')
                        objects_deleted = s3lib.resource_op({'obj': objects,
                                                             'resource': 'delete',
                                                             'args': None})
                        log.info('objects_deleted: %s' % objects_deleted)
                        if objects_deleted is False:
                            raise TestExecError('Resource execution failed: Object deletion failed')
                        if objects_deleted is not None:
                            response = HttpResponseParser(objects_deleted[0])
                            if response.status_code == 200:
                                log.info('objects deleted ')
                            else:
                                raise TestExecError("objects deletion failed")
                        else:
                            raise TestExecError("objects deletion failed")
                        # wait for object delete info to sync
                        time.sleep(60)
                        log.info('deleting bucket: %s' % bucket.name)
                        # bucket_deleted_status = s3_ops.resource_op(bucket, 'delete')
                        bucket_deleted_status = s3lib.resource_op({'obj': bucket,
                                                                   'resource': 'delete',
                                                                   'args': None})
                        log.info('bucket_deleted_status: %s' % bucket_deleted_status)
                        if bucket_deleted_status is not None:
                            response = HttpResponseParser(bucket_deleted_status)
                            if response.status_code == 204:
                                log.info('bucket deleted ')
                            else:
                                raise TestExecError("bucket deletion failed")
                        else:
                            raise TestExecError("bucket deletion failed")
        test_info.success_status('test passed')
        sys.exit(0)
    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
        test_info.failed_status('test failed')
        sys.exit(1)
    except TestExecError as e:
        log.info(e)
        log.info(traceback.format_exc())
        test_info.failed_status('test failed')
        sys.exit(1)


if __name__ == '__main__':
    project_dir = os.path.abspath(os.path.join(__file__, "../../.."))
    test_data_dir = 'test_data'
    TEST_DATA_PATH = (os.path.join(project_dir, test_data_dir))
    log.info('TEST_DATA_PATH: %s' % TEST_DATA_PATH)
    if not os.path.exists(TEST_DATA_PATH):
        log.info('test data dir not exists, creating.. ')
        os.makedirs(TEST_DATA_PATH)
    parser = argparse.ArgumentParser(description='RGW S3 Automation')
    parser.add_argument('-c', dest="config",
                        help='RGW Test yaml configuration')
    args = parser.parse_args()
    yaml_file = args.config
    config = Config()
    config.max_objects = None
    if yaml_file is None:
        config.objects_count = 2
        config.objects_size_range = {'min': 10, 'max': 50}
    else:
        with open(yaml_file, 'r') as f:
            doc = yaml.load(f)
        config.objects_count = doc['config']['objects_count']
        config.objects_size_range = {'min': doc['config']['objects_size_range']['min'],
                                     'max': doc['config']['objects_size_range']['max']}
        config.test_ops = doc['config']['test_ops']
    log.info('objects_count: %s\n'
             'objects_size_range: %s\n'
             % (config.objects_count, config.objects_size_range))
    log.info('test_ops: %s' % config.test_ops)
    test_exec(config)
