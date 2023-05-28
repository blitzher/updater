import re
import requests
import os
import sys
import time
import json
import shutil
from os import path
import py7zr as zp
from tqdm import tqdm

os.chdir(os.path.dirname(__file__))


class Task:
    def __init__(self, obj):
        try:
            self.name = obj['name']
            self.url = obj['url']
            self.regex = obj['regex']
            self.download = obj['download']
            self.target = obj['target']

            # optional params
            self.zip = obj['zip?'] if ('zip?' in obj) else False
            self.reverse = obj['reverse?'] if ('reverse?' in obj) else False
            self.redir = obj['redir?'] if ('redir?' in obj) else False
        except:
            raise SyntaxError(obj)

    def execute(self):
        print("Looking for %s updates..." % self.name)
        website = requests.get(self.url).text

        # find all versions, and selects the most up-to-date version
        version = sorted(re.findall(self.regex, website))
        if (self.reverse):
            version = version[::-1]
        version = version[0]

        if (self.redir):
            redir = requests.get(self.redir['url'] % version.strip("/")).text
            version = re.findall(self.redir['regex'], redir)[0]

        print("Found new version: %s!" % version)
        os.chdir(self.target % "")

        # if the most up-to-date version is not found
        if not os.path.exists(version):
            # remove older zip versions beforehand
            for element in os.listdir(os.curdir):
                if (element.endswith(".zip") or element.endswith(".7z")):
                    os.remove(element)

            # download to disk
            save_name = version.split("/")[-1]

            download_url(self.download % version, save_name)
            remove_old(self, version)
        else:
            print("%s up to date" % self.name)
            print()
            return

        # unpack to local folder if WinRAR is installed
        if os.path.exists(options['winrar-dir']) and self.zip:
            print("Decompressing %s..." % save_name)

            # -IBCK : run in background
            os.system('"%s" x -Y -IBCK -RI15 %s' %
                      (options['winrar-dir'], save_name))

            print("%s up to date" % self.name)
        elif (self.zip):
            print("Can't decompress %s: Cannot find WinRAR" % (self.name))

        print()


with open("./daily.json", "r") as f:
    file = json.load(f)

options = file['options']
tasks = file['tasks']
paused = file['paused']


def remove_extention(file_name):
    return ".".join(file_name.split(".")[:-1])


def remove_old(task, current):
    os.chdir(task.target % "")
    current = remove_extention(current)
    for file in os.listdir(os.curdir):

        # find regex from task
        folder_regex = task.redir['regex'] if task.redir else task.regex

        #
        folder_regex = remove_extention(folder_regex)[0:-1] + '$'
        is_match = re.match(folder_regex, file)

        if re.match(folder_regex, file) and file != current:
            print("Removing old version {}".format(file))
            if (path.isdir(file)):
                shutil.rmtree(file, ignore_errors=True)
            else:
                os.remove(file)


def download_url(url, save_path, chunk_size=128):

    # fix double slashes
    url = re.sub("[\/]+", "/", url)
    # put the 'https://' double slash back
    url = re.sub("[\/]", "//", url, count=1)
    save_path = re.sub("[\/]+", "/", save_path)

    r = requests.get(url, stream=True)
    desc = "-".join(url.split('/')[-1].split("-")[0:2])

    # wrap the opening of file with tqdm for loading bar
    with tqdm.wrapattr(open(save_path, "wb"), "write",
                       miniters=1, desc=desc,
                       total=int(r.headers.get('content-length', 0))) as fout:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fout.write(chunk)


def main(args):

    if (len(args) > 0):
        task_to_run = args[0]
        for t in tasks + paused:
            t = Task(t)
            if (t.name == task_to_run):
                t.execute()
                break
        else:
            print("Task %s not found!" % task_to_run)
            return

    else:
        for t in tasks:
            task = Task(t)
            task.execute()

    print("Updated succesfully")
    time.sleep(3)


if __name__ == '__main__':
    main(sys.argv[1:])
