# coding: utf-8

##########################################################################
# name: OCI-ShowBackups.py
# task: list OCI Compute Volume backups
# author: Florian Bonneville
# version: 1.0 - february 21th 2023
#
# disclaimer: this is not an official Oracle application,  
# it does not supported by Oracle Support
##########################################################################

import oci
import csv
import time
import argparse
import datetime
from modules.identity import *
from modules.storage import *
from modules.compute import *

##########################################################################
# get command line arguments
##########################################################################

parser=argparse.ArgumentParser()

parser.add_argument('-cs', action='store_true', default=False, dest='is_delegation_token', help='Use CloudShell Delegation Token for authentication')
parser.add_argument('-cf', action='store_true', default=False, dest='is_config_file', help='Use local OCI config file for authentication')
parser.add_argument('-cfp', default='~/.oci/config', dest='config_file_path', help='Path to your OCI config file, default: ~/.oci/config')
parser.add_argument('-cp', default='DEFAULT', dest='config_profile', help='config file section to use, default: DEFAULT')

parser.add_argument('-c', default='', dest='report_comp', help='Compartment OCID to store the report')
parser.add_argument('-b', default='', dest='report_bucket', help='Bucket name to store the report, default: reports_YOUR_TENANT_NAME')
parser.add_argument('-rf', default='~/', dest='report_folder', help='folder path to store the report')
parser.add_argument('-rn', default='compute_backups_', dest='report_name', help='name of the csv report')

parser.add_argument('-nocloud', action='store_true', default=False, dest='nocloud', help='Do not move report to OCI Storage')

parser.add_argument('-tlc', default='', dest='target_comp', help='define the compartment name to analyze, default is your root compartment')
parser.add_argument('-rg', default='', dest='target_region', help='define regions to analyze, default is all regions')

cmd=parser.parse_args()

##########################################################################
# clear shell screen
##########################################################################

clear()

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
# start printing output
##########################################################################

print()
print(green+f"{'*'*89:89}")
print(green+f"{'*'*5:5} {'Analysis:':15} {'started':20} {'OCI Show Backups':40} {'*'*5:5}")

##########################################################################
# set csv report folder & name
##########################################################################

if cmd.report_folder:
    report_folder=cmd.report_folder
else:
    report_folder='~/'

if cmd.report_name:
    report_name=cmd.report_name
else:
    report_name='compute_backups_'

report_folder = path_expander(report_folder)
check_folder(report_folder, output=True)

##########################################################################
# oci authentication
##########################################################################

config, signer, oci_tname=create_signer(cmd.config_file_path, cmd.config_profile, cmd.is_delegation_token, cmd.is_config_file)
tenancy_id=config['tenancy']

##########################################################################
# get current date and time
##########################################################################

now=datetime.datetime.today()
now=now.strftime('%Y%m%d_%H%M')
report_name=report_name+str(now)+'.csv'
csv_report=report_folder+report_name
print(green+f"{'*'*5:5} {'Report:':15} {'name':20} {report_name:40} {'*'*5:5}")

##########################################################################
# set top level compartment OCID to filter on a Compartment
##########################################################################

if cmd.target_comp:
    top_level_compartment_id=cmd.target_comp
else:
    top_level_compartment_id=tenancy_id

##########################################################################
# init csv report
##########################################################################

with open(csv_report, mode='w') as csv_file:
    fieldnames=['region', 'availability_domain', 'compartment', 'compute_instance', 'volume_type', 'backup_type', 'backup_created', 'size_in_gbs', 'source_type', 'lifecycle_state', 'backup_name']
    writer=csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
csv_file.close

##########################################################################
# init oci service clients
##########################################################################

identity_client=oci.identity.IdentityClient(config=config, signer=signer)
obj_storage_client=oci.object_storage.ObjectStorageClient(config=config, signer=signer)

##########################################################################
# check oci compartment & bucket
##########################################################################

if cmd.nocloud == False:
    nocloud="False"
    if cmd.report_comp == '':
      cmd.report_comp=tenancy_id

    if cmd.report_bucket == '':
        cmd.report_bucket='oci_reports_'+oci_tname

    compartment_name=identity_client.get_compartment(cmd.report_comp).data.name
    print(green+f"{'*'*5:5} {'Compartment:':15} {'report':20} {compartment_name:40} {'*'*5:5}")
    check_bucket(obj_storage_client, cmd.report_comp, cmd.report_bucket, tenancy_id)
else:
    nocloud="True"

print(green+f"{'*'*5:5} {'Nocloud:':15} {'value':20} {nocloud:40} {'*'*5:5}")

if cmd.target_region == '':
    print(green+f"{'*'*5:5} {'Regions:':15} {'analyzed':20} {'all':40} {'*'*5:5}")
else:
    print(green+f"{'*'*5:5} {'Regions:':15} {'analyzed':20} {cmd.target_region:40} {'*'*5:5}")

my_compartments=get_compartment_list(identity_client, top_level_compartment_id)
all_regions=get_region_subscription_list(identity_client, tenancy_id, cmd.target_region)

##########################################################################
# print screen header
##########################################################################

print(green+f"{'*'*89:89}\n")
print(f"{'REGION':15}  {'AD':6}  {'COMPARTMENT':15}  {'INSTANCE':15}  {'TYPE':6}  {'BACKUP_TYPE':12}  {'CREATED_ON':18}  {'SIZE_GBS':10}  {'SOURCE':11}  {'STATE':12}  {'BACKUP_NAME':15}\n")

##########################################################################
# start analysis
##########################################################################

for region in all_regions:    
    s=' '*50
    config['region']=region.region_name
    core_client=oci.core.ComputeClient(config=config, signer=signer)
    blk_storage_client=oci.core.BlockstorageClient(config=config, signer=signer)

    if cmd.target_region == '' or region.region_name in cmd.target_region:

        for compartment in my_compartments:

            print(default_c+'   {}: Analyzing compartment: {}'.format(region.region_name, compartment.name),end=s+'\r')

            my_instances=list_instances(core_client, compartment.id)

            for instance in my_instances:
                print(default_c+'   {}: Analyzing instance: {}'.format(region.region_name, instance.display_name),end=s+'\r')
                my_bootvol=list_instances_bootvol(core_client, instance.availability_domain, compartment.id, instance.id)

                for bootvol in my_bootvol:
                    my_bootvol_backups=list_boot_volume_backups(blk_storage_client, compartment.id, bootvol.boot_volume_id)

                    for boot_backup in my_bootvol_backups:
                        volume_type='boot'

                        print(white+f'{region.region_name:15}  {instance.availability_domain[-4:]:6}  {compartment.name[0:13]:15}  {instance.display_name[0:13]:15}  {volume_type:6}  {boot_backup.type:12}  {str(boot_backup.time_created)[0:16]:18}  {boot_backup.unique_size_in_gbs:<10}  {boot_backup.source_type:11}  {boot_backup.lifecycle_state:12}  {boot_backup.display_name[0:13]:15}')

                        with open(csv_report, mode='a', newline='') as csvfile:
                            fieldnames=['region', 'availability_domain', 'compartment', 'compute_instance', 'volume_type', 'backup_type', 'backup_created', 'size_in_gbs', 'source_type', 'lifecycle_state', 'backup_name']
                            writer=csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow({'region': instance.region, 'availability_domain': instance.availability_domain, 'compartment': compartment.name, 'compute_instance': instance.display_name, 'volume_type': volume_type, 'backup_type': boot_backup.type, 'backup_created': (boot_backup.time_created).strftime("%Y-%m-%d %H:%M:%S"), 'size_in_gbs': boot_backup.unique_size_in_gbs, 'source_type': boot_backup.source_type, 'lifecycle_state': boot_backup.lifecycle_state, 'backup_name': boot_backup.display_name})
                            time.sleep(2)

                my_blk_attach=list_instances_volattach(core_client, instance.availability_domain, compartment.id, instance.id)

                for blkattach in my_blk_attach:
                    my_blk_backups=list_volume_backups(blk_storage_client, compartment.id, blkattach.volume_id)

                    for blk_backup in my_blk_backups:
                        volume_type='block'
                        print(yellow+f'{region.region_name:15}  {instance.availability_domain[-4:]:6}  {compartment.name[0:13]:15}  {instance.display_name[0:13]:15}  {volume_type:6}  {blk_backup.type:12}  {str(blk_backup.time_created)[0:16]:18}  {blk_backup.unique_size_in_gbs:<10}  {blk_backup.source_type:11}  {blk_backup.lifecycle_state:12}  {blk_backup.display_name[0:13]:15}')

                        with open(csv_report, mode='a', newline='') as csvfile:
                            fieldnames=['region', 'availability_domain', 'compartment', 'compute_instance', 'volume_type', 'backup_type', 'backup_created', 'size_in_gbs', 'source_type', 'lifecycle_state', 'backup_name']
                            writer=csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow({'region': instance.region, 'availability_domain': instance.availability_domain, 'compartment': compartment.name, 'compute_instance': instance.display_name, 'volume_type': volume_type, 'backup_type': blk_backup.type, 'backup_created': (blk_backup.time_created).strftime("%Y-%m-%d %H:%M:%S"), 'size_in_gbs': blk_backup.unique_size_in_gbs, 'source_type': blk_backup.source_type, 'lifecycle_state': blk_backup.lifecycle_state, 'backup_name': blk_backup.display_name})
                            time.sleep(2) 

##########################################################################
# move report to oci 
##########################################################################
if cmd.nocloud == False:
    upload_file(obj_storage_client, cmd.report_bucket, csv_report, report_name, tenancy_id)
else:
    print('\n')

# reset terminal color
print(' '*50)
print(default_c)
