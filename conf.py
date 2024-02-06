# Begin: 2024-01-31
import os.path

PLUGINS_DIR = "E:/dev/qgis_plugins"
TEMP_XML_PATH = PLUGINS_DIR + "/temp.xml"
CURRENT_XML_PATH = PLUGINS_DIR + "/plugins.xml"
LAST_XML_PATH = PLUGINS_DIR + "/last.xml"
DOWNLOAD_LIST_PATH = PLUGINS_DIR + "/download.list"
ARCHIVE_DIR = PLUGINS_DIR + "/archives"
STABLE_PLUGINS = PLUGINS_DIR + "/stable"
INDEX_DIRNAME = 4
INDEX_VERSION = 6
# url: https://plugins.qgis.org/plugins/citygen/version/0.3/download/
# zip filename: citygen-0.3.zip
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "template")
TEMPLATE_HTML = os.path.join(TEMPLATE_DIR, "html.html")
TEMPLATE_RECORD = os.path.join(TEMPLATE_DIR, "record.html")

QGIS_VERSION = "3.34"

PLUGINS_URL = "https://plugins.qgis.org/plugins/"
PLUGINS_XML_URL_TMPL = PLUGINS_URL + "plugins.xml?qgis={}"
