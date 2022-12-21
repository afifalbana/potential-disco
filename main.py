#!/usr/bin/env python
# Author: Afif Albana, M
# Version: 1.0

import time
import os
import yaml
import requests
import mysql.connector as mysql

class checkDomain:
    def __init__(self):
        self.hosts = []
        self.tokens = []

        # Get variable from config.yaml
        self.work_dir = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(self.work_dir + '/config.yaml') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

        for item in config.get('scrap_config'):
            if 'scrap_interval' in item:
                self.scrap_interval = int(item['scrap_interval'])

        for item in config.get('db_config'):
            if 'db_plesk_name' in item:
                self.db_plesk_name = item['db_plesk_name']
            if 'db_app_name' in item:
                self.db_app_name = item['db_app_name']
            if 'db_app_user' in item:
                self.db_app_user = item['db_app_user']
            if 'db_app_password' in item:
                self.db_app_password = item['db_app_password']
            if 'db_app_host' in item:
                self.db_app_host = item['db_app_host']

        for item in config['api_access']:
            if 'hosts' in item:
                for host in item['hosts']:
                    self.hosts.append(host)
            if 'api_tokens' in item:
                for token in item['api_tokens']:
                    self.tokens.append(token)

    def mysql_connect(self):
        connect = mysql.connect(
            user=self.db_app_user,
            password=self.db_app_password,
            host=self.db_app_host
        )
        return connect

    def new_domain(self):
        connect = self.mysql_connect()
        cursor = connect.cursor()

        sql = "SELECT id,name FROM {0}.domains WHERE `id` NOT IN (select id from {1}.domains)".format(self.db_plesk_name, self.db_app_name)
        cursor.execute(sql)

        new_domain_id = []
        for item in cursor:
            new_domain_id.append(item)

        connect.close()
        return new_domain_id

    def old_domain(self):
        connect = self.mysql_connect()
        cursor = connect.cursor()

        sql = "SELECT id,name FROM {0}.domains WHERE `id` NOT IN (select id from {1}.domains)".format(self.db_app_name, self.db_plesk_name)
        cursor.execute(sql)

        removed_domain_id = []
        for item in cursor:
            removed_domain_id.append(item)

        connect.close()
        return removed_domain_id

    def add_domain(self):
        connect = self.mysql_connect()
        cursor = connect.cursor()

        new_domain = self.new_domain()
        if new_domain:
            # API request to add domain restricted
            for node, token in zip(self.hosts, self.tokens):
                header = {"X-API-KEY": token, "Accept": "application/json", "Content-Type": "application/json"}
                url = "https://{0}:8443/api/v2/cli/domain_restriction/call".format(node)

                for id, domain_name in new_domain:
                    param = {"params": ["--add", "-name", domain_name]}
                    resp = requests.post(url, headers=header, json=param)
                    if resp.status_code != 200:
                        print("POST domain_restriction/call {0}".format(resp.status_code))

            # Insert added domain to database
            sql = """INSERT INTO {0}.domains
            SELECT id,cr_date,name,displayName,parentDomainID FROM {1}.domains
            WHERE `id` NOT IN (SELECT id FROM {2}.domains)
            """.format(self.db_app_name, self.db_plesk_name, self.db_app_name)

            cursor.execute(sql)
            connect.commit()
            connect.close()
            print("Check completed. New domain added.")
        else:
            print("Check completed. No new domain.")

    def remove_domain(self):
        connect = self.mysql_connect()
        cursor = connect.cursor()

        old_domain = self.old_domain()
        if old_domain:
            # Api request to remove domain prohibited
            for node, token in zip(self.hosts, self.tokens):
                header = {"X-API-KEY": token, "Accept": "application/json", "Content-Type": "application/json"}
                url = "https://{0}:8443/api/v2/cli/domain_restriction/call".format(node)

                for id, domain_name in old_domain:
                    param = {"params": ["--remove", "-name", domain_name]}
                    resp = requests.post(url, headers=header, json=param)
                    if resp.status_code != 200:
                        print("POST domain_restriction/call {0}".format(resp.status_code))

            # Delete old domain from database
            for id, domain_name in old_domain:
                sql = "DELETE FROM {0}.domains WHERE id={1}".format(self.db_app_name, id)
                cursor.execute(sql)
                connect.commit()
            connect.close()
            print("Check completed. Old domain removed.")
        else:
            print("Check completed. No old domain.")

    def main_program(self):
        while True:
            try:
                self.add_domain()
                self.remove_domain()
                time.sleep(self.scrap_interval)
            except:
                print("Something error. Call Afif for support.")
                break

if __name__ == '__main__':
    checkDomain().main_program()
