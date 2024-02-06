# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: MIT

from ast import NodeVisitor, parse as astParse
import configparser
import os.path
import urllib.request
import shutil
import time
from xml.etree import ElementTree
import zipfile

from conf import ARCHIVE_DIR, CURRENT_XML_PATH, PLUGINS_DIR, PLUGINS_URL

# convenient functions


def downloadFile(url, filepath, delay=0):
    print("Downloading {}...".format(url), end=" ", flush=True)

    if delay:
        time.sleep(delay)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, None, headers)
        response = urllib.request.urlopen(req)
        data = response.read()
        with open(filepath, mode="wb") as f:
            f.write(data)
    except Exception as e:
        print("failed")
        raise e
    else:
        print("ok")
        return data


def downloadFiles(urls, count=-1, interval=5):
    """
    :param count: if -1, this function attempts to download all files in download list file
    """

    success = skipped = error = 0

    urls = urls[:count] if count != -1 else urls
    print("Starting to download {} files.".format(len(urls)))

    for url in urls:
        e = url.split("/")
        filename = e[-1]
        path = filename     #TODO
        if os.path.exists(path):
            print("{} already exists. Skipped.")
            skipped += 1
            continue

        try:
            data = downloadFile(url, path, delay=interval)
            success += 1
        except:
            error += 1
            continue

    print("{} files downloaded. {} errors. {} skipped.".format(success, error, skipped))


def pluginsDir(*subdirs):
    return os.path.join(PLUGINS_DIR, *subdirs)


def pluginsUrl(*subdirs):
    return "/".join(PLUGINS_URL, list(subdirs))


def removeDir(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def removeFile(path):
    if os.path.exists(path):
        os.remove(path)


def removeFiles(paths):
    for p in paths:
        removeFile(p)


def renameFile(path, to_path):
    removeFile(to_path)
    if os.path.exists(path):
        os.rename(path, to_path)


def getPlugins(xml_path=CURRENT_XML_PATH, exclude_experimental=True, verbose=False):
    with open(xml_path, "r", encoding="utf-8") as f:
        xml = f.read()

    tree = ElementTree.fromstring(xml)
    for plugin in tree:
        experimental = bool(plugin.find("experimental").text == "True")
        if exclude_experimental and experimental:
            continue

        yield plugin


def getVersionFromMetadata(data):
    cp = configparser.ConfigParser()
    cp.read_string(data)
    version = cp["general"]["version"]
    results = []
    for e in version.replace("version", "").replace("Version", "").strip().split("."):
        try:
            v = str(int(e))
        except:
            v = e
        results.append(v)
    return ".".join(results)


def getPluginVersion(path):
    """
    :param path: path to a plugin directory or its metadata.txt
    """
    path = path + "/metadata.txt" if os.path.isdir(path) else path
    with open(path, encoding="utf-8") as f:
        metadata = f.read()

    return getVersionFromMetadata(metadata)


def getZippedPluginVersion(filepath):
    with zipfile.ZipFile(filepath) as zip:
        with zipfile.open(zip.namelist()[0] + "metadata.txt") as f:
            metadata = f.read().decode("utf-8")

    return getVersionFromMetadata(metadata)


def unzip(filepath, dest):
    shutil.unpack_archive(filepath, dest)


class PluginAnalyzer(NodeVisitor):

    def __init__(self):
        self.clear()

    def clear(self):
        self.size = 0
        self.extensions = set()
        self.dependencies = {"": set()}
        self.errors = []

    def visit_Import(self, node):
        for name in node.names:
            self.dependencies[""].add(name.name)

    def visit_ImportFrom(self, node):
        if node.module is None or node.level > 0:
            # https://stackoverflow.com/a/58847554
            # if node.module is missing it's a "from . import ..." statement
            # if level > 0 it's a "from .submodule import ..." statement
            return

        if node.module not in self.dependencies:
            self.dependencies[node.module] = set()

        for name in node.names:
            self.dependencies[node.module].add(name.name)

    def analyze(self, plugin_dir, verbose=False):

        for root, dirs, files in os.walk(plugin_dir):
            for name in files:
                path = os.path.join(root, name)

                self.size += os.path.getsize(path)

                ext = os.path.splitext(name)[1]
                self.extensions.add(ext)

                if ext == ".py":
                    with open(path, encoding="utf-8", errors="replace") as f:
                        text = f.read()

                    if len(text) > 0 and text[0] == "\ufeff":     # BOM
                        text = text[1:]

                    try:
                        self.visit(astParse(text))
                    except SyntaxError as e:
                        if "{SyntaxError}" not in self.dependencies:
                            self.dependencies["{SyntaxError}"] = set()
                        self.dependencies["{SyntaxError}"].add(name)

                        msg = "SyntaxError: {} ({})".format(path, e)
                        self.errors.append(msg)
                        if verbose:
                            print(msg)

        dirname = os.path.basename(plugin_dir)
        self.dependencies = {k: v for k, v in self.dependencies.items() if not k.startswith(dirname)}

    def results(self):
        d = []
        for k, v in sorted(self.dependencies.items()):
            d.append("[{}] {}".format(k, ", ".join(sorted(v))))

        return {
            "size": "{:,} kb".format(int(self.size / 1000)),
            "size_sort": "{:0>7}".format(int(self.size / 100)),
            "extensions": ", ".join(sorted(self.extensions)),
            "dependencies": "<br>\n".join(d)
        }


def getOldZipFilenames():
    filenames = [plugin.find("file_name").text for plugin in getPlugins(exclude_experimental=False)]
    archives = [name for name in os.listdir(ARCHIVE_DIR) if name.endswith(".zip")]
    return sorted(set(archives) - set(filenames))
