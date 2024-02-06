# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: MIT

import os
import time
from conf import CURRENT_XML_PATH, ARCHIVE_DIR, INDEX_DIRNAME, PLUGINS_DIR, PLUGINS_XML_URL_TMPL, STABLE_PLUGINS, QGIS_VERSION, TEMPLATE_HTML, TEMPLATE_RECORD
from utils import downloadFile, getOldZipFilenames, getPlugins, getPluginVersion, removeDir, removeFile, unzip, PluginAnalyzer


def fetchXml():
    removeFile(CURRENT_XML_PATH)
    downloadFile(PLUGINS_XML_URL_TMPL.format(QGIS_VERSION), CURRENT_XML_PATH)


def fetchPlugins(count=-1, interval=5):
    """
    :param count: if -1, this function attempts to download all files in download list file
    """

    success = error = total = 0

    items = []
    for plugin in getPlugins():
        url = plugin.find("download_url").text
        filename = plugin.find("file_name").text
        path = "{}/{}".format(ARCHIVE_DIR, filename)
        if not os.path.exists(path):
            items.append((url, filename))
        total += 1

    print("Total {} plugins. {} plugins already exists.".format(total, total - len(items)))

    if count != -1:
        items = items[:count]

    print("Starting to download {} plugins.".format(len(items)))

    for i, item in enumerate(items):
        url, filename = item

        print("{}/{}".format(i + 1, len(items)), end=" ")

        try:
            data = downloadFile(url, ARCHIVE_DIR + "/" + filename, delay=interval)
            success += 1
        except KeyboardInterrupt:
            break
        except:
            error += 1
            continue

    print()
    print("{} files downloaded. {} errors.".format(success, error))


def unzipPlugins(exclude_experimental=True, verbose=False):
    unzipped = skipped = updated = total = 0
    new_plugins = []
    updated_plugins = []
    for plugin in getPlugins(exclude_experimental=exclude_experimental):
        total += 1

        url = plugin.find("download_url").text
        e = url.split("/")
        dirname = e[INDEX_DIRNAME]

        v = plugin.attrib["version"]
        zip_filename = plugin.find("file_name").text

        if verbose:
            print(zip_filename, end="...")

        dest_path = STABLE_PLUGINS + "/" + dirname
        update_flag = False
        if os.path.exists(dest_path):
            exv = getPluginVersion(dest_path)
            if exv == v:
                skipped += 1
                if verbose:
                    print("skipped")
                continue

            removeDir(dest_path)
            updated += 1
            update_flag = True
            updated_plugins.append("{}: {} -> {}".format(dirname, exv, v))

        else:
            new_plugins.append("{}: {}".format(dirname, v))

        unzip(ARCHIVE_DIR + "/" + zip_filename, STABLE_PLUGINS)
        unzipped += 1
        if verbose:
            print("unzipped" + " (updated)" if update_flag else "")

    print("Unzipped {} files. {} plugins updated. {} plugins are already latest version. Total {} plugins.".format(unzipped, updated, skipped, total))
    if new_plugins:
        print("*** New plugins ***")
        for s in new_plugins:
            print(s)
    if updated_plugins:
        print("*** Updated plugins ***")
        for s in updated_plugins:
            print(s)


def generateHTML(out_dir, exclude_experimental=True, verbose=False):

    with open(TEMPLATE_HTML, encoding="utf-8") as f:
        tmpl_html = f.read()

    tmpl_htmlpart = tmpl_html.split("{records}")

    with open(TEMPLATE_RECORD, encoding="utf-8") as f:
        tmpl_record = f.read()

    print()
    print("Reading metadata...", end=" ", flush=True)

    records = []
    for plugin in getPlugins(exclude_experimental=exclude_experimental):
        url = plugin.find("download_url").text
        e = url.split("/")
        dirname = e[INDEX_DIRNAME]
        plugin_dir = STABLE_PLUGINS + "/" + dirname

        d = {
            "dirname": dirname,
            "name": plugin.attrib["name"],
            "version": plugin.attrib["version"],
            "create_date": plugin.find("create_date").text.split("T")[0],
            "update_date": plugin.find("update_date").text.split(".")[0].replace("T", " "),
            "downloads": "{:,}".format(int(plugin.find("downloads").text)),
            "average_vote": "{:.1f}".format(float(plugin.find("average_vote").text)),
            "trusted": "(Trusted)" if plugin.find("trusted").text == "True" else ""
        }

        for k in ["author_name", "description", "about", "tags", "repository", "rating_votes"]:
            d[k] = plugin.find(k).text

        records.append(d)

    print("ok")
    print("Analyzing plugins")

    stats = {
        "Total": len(records),
        "SyntaxErrors": 0
    }

    analyzer = PluginAnalyzer()
    t0 = time.time()

    for i, d in enumerate(records):
        plugin_dir = STABLE_PLUGINS + "/" + d["dirname"]

        analyzer.clear()
        analyzer.analyze(plugin_dir, verbose=verbose)
        d.update(analyzer.results())

        stats["SyntaxErrors"] += len(analyzer.errors)

        if i % 100 == 0:
            print(".", end="", flush=True)

    print(" ok")
    print("Analysis completed in {:.1f} secs".format(time.time() - t0))
    print(stats)

    records = sorted(records, key=lambda x: x["update_date"], reverse=True)
    records_html = "\n".join(tmpl_record.format(**r) for r in records)

    filename = out_dir + "/" + "index.html"
    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.write(tmpl_htmlpart[0])
        f.write(records_html)
        f.write(tmpl_htmlpart[1])

    print("Summary has been written to {}.".format(filename))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    # TODO: include experimental plugins
    parser.add_argument("-u", "--update_xml", help="Fetch plugins.xml from QGIS Python plugins website", action="store_true")
    parser.add_argument("-s", "--no_fetch_plugins", help="Skip downloading unfetched plugins.", action="store_true")
    parser.add_argument("-n", "--count",type=int, default=-1, help="The number of plugins to download")
    parser.add_argument("-i", "--interval", type=int, default=5, help="Time interval (in seconds)")
    parser.add_argument("-o", "--out_dir", type=str, default="", help="Summary output directory. If not specified, do not output summary files.")
    parser.add_argument("--clean", help="remove zip files of old versions", action="store_true")
    parser.add_argument("-v", "--verbose", help="", action="store_true")

    args = parser.parse_args()

    if not os.path.exists(PLUGINS_DIR):
        print("Directory to store plugins.xml and *.zip not exists. See conf.py.")

    if args.update_xml:
        fetchXml()

    if not args.no_fetch_plugins:
        fetchPlugins(args.count, args.interval)
        unzipPlugins(verbose=args.verbose)

    if args.out_dir:
        generateHTML(args.out_dir, verbose=args.verbose)
    else:
        print("Output directory not specified. Generating summary skipped.")

    if args.clean:
        files = getOldZipFilenames()
        if len(files):
            # confirm
            print("There are {} old archives:".format(len(files)))
            for f in files:
                print(f)
            ans = input("Are you sure you want to remove these files? [y/n]:").lower()
            if ans == "y":
                for f in files:
                    removeFile(ARCHIVE_DIR + "/" + f)

                print("{} files removed.".format(len(files)))

        else:
            print("There are no old archives.")
        #TODO: remove directories of plugins that has been removed from plugins.xml
