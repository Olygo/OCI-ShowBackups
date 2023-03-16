# coding: utf-8

import oci
import os
import time

##########################################################################
# set colors
##########################################################################
black='\033[0;30m'
red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
blue='\033[0;34m'
magenta='\033[0;35m'
cyan='\033[0;36m'
white='\033[0;37m'
default_c='\033[0m'

##########################################################################
# expand local path
##########################################################################

def path_expander(path):

    path = os.path.expanduser(path)
    
    return path

##########################################################################
# check if bucket already exists
##########################################################################

def check_bucket(obj_storage_client, report_comp, report_bucket, tenancy_id):

    my_namespace = obj_storage_client.get_namespace(compartment_id=tenancy_id).data
    all_buckets = obj_storage_client.list_buckets(my_namespace,report_comp).data
    bucket_etag=''

    for bucket in all_buckets:
        if bucket.name == report_bucket:
            print(green+f"{'*'*5:5} {'Bucket:':15} {'found':20} {bucket.name:40} {'*'*5:5}")
            bucket_etag=bucket.etag

    if len(bucket_etag) < 1:
        print(yellow+f"{'*'*5:5} {'Bucket:':15} {'creating':20} {report_bucket:40} {'*'*5:5}")

        create_bucket_details = oci.object_storage.models.CreateBucketDetails(
            public_access_type = 'NoPublicAccess',
            storage_tier = 'Standard',
            versioning = 'Disabled',
            name = report_bucket,
            compartment_id = report_comp
            )
        result = obj_storage_client.create_bucket(my_namespace, create_bucket_details)                
        result_response = obj_storage_client.get_bucket(my_namespace, report_bucket)

        wait_until_bucket_available_response = oci.wait_until(obj_storage_client,result_response,'etag',result_response.data.etag)
        print(green+f"{'*'*5:5} {'Bucket:':15} {'created':20} {wait_until_bucket_available_response.data.name:40} {'*'*5:5}")

    return

##########################################################################
# move csv report to oci
##########################################################################

def upload_file(obj_storage_client, report_bucket, csv_report, report_name, tenancy_id):
    namespace = obj_storage_client.get_namespace(compartment_id=tenancy_id).data

    ##########################################################################
    # upload report to oci
    ##########################################################################

    with open(csv_report, 'rb') as in_file:
        filename = os.path.basename(csv_report)
        upload_response = obj_storage_client.put_object(
            namespace,
            report_bucket,
            report_name,
            in_file)

    ##########################################################################
    # list objects in bucket and check md5 of uploaded file
    ##########################################################################

    object_list = obj_storage_client.list_objects(namespace, report_bucket, fields=['md5'])

    for item in object_list.data.objects:
        if item.md5 == upload_response.headers['opc-content-md5']:
            print(' '*100)
            print(green+f"{'*'*89:89}")
            print(green+f"{'*'*5:5} {'Upload:':15} {'success':20} {item.name:40} {'*'*5:5}")
            print(green+f"{'*'*5:5} {'MD5 checksum:':15} {'success':20} {item.md5:40} {'*'*5:5}")
            print(green+f"{'*'*89:89}")
            print()
            print()

            ##########################################################################
            # remove local file
            ##########################################################################
            os.remove(csv_report)
            break
        
        else:
            pass

    return

##########################################################################
# retrieve bucket info
##########################################################################

def get_bucket_info(obj_storage_client, report_bucket, tenancy_id):

    time.sleep(10)
    namespace = obj_storage_client.get_namespace(compartment_id=tenancy_id).data 
    report_bucket_size = obj_storage_client.get_bucket(namespace,report_bucket,fields=['approximateCount','approximateSize'])
    bucketfiles = report_bucket_size.data.approximate_count
    bucketsize = report_bucket_size.data.approximate_size/(1024*1024*1024)
       
    return bucketfiles, bucketsize

##########################################################################
# check if local folder already exists
##########################################################################

def check_folder(folder, **output):
    if not os.path.exists(folder):
        os.mkdir(folder)
        if output:
            print(yellow+f"{'*'*5:5} {'Folder:':15} {'creating':20} {folder:40} {'*'*5:5}")
    else:
        if output:
            print(green+f"{'*'*5:5} {'Folder:':15} {'found':20} {folder:40} {'*'*5:5}")