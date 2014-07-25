import requests, HTMLParser
from lxml import etree
from datetime import datetime, timedelta
from copy import deepcopy
from roar2doar.core import app
from roar2doar import oarr

NS = "{http://eprints.org/ep2/data/2.0}"

h = HTMLParser.HTMLParser()

def _normalise_date(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return None

def _extract_repo_type(roar_type):
    mapping = {
        "institutional" : "Institutional",
        "subject" : "Subject"
    }
    return mapping.get(roar_type)

def _extract_content_type(roar_type):
    mapping = {
        "journal" : "Journal articles",
        "theses" : "Theses and dissertations",
        "database" : "Datasets",
        "researchdata" : "Datasets",
        "opendata" : "Datasets",
        "learning" : "Learning Objects",
    }
    return mapping.get(roar_type)

def _extract_status(roar_type):
    mapping = {
        "demonstration" : "Trial"
    }
    return mapping.get(roar_type)

def _normalise_value(val, unescape=False, lower=False, cast=None, aslist=False, prepend=None, valuefunction=None):
    if prepend is not None:
        val = prepend + val
    if unescape:
        val = h.unescape(val)
    if lower:
        val = val.lower()
    if cast is not None:
        val = cast(val)
    if valuefunction is not None:
        val = valuefunction(val)

    if val is None: # we need to check in case it got set to None by any of the preceeding steps
        return None

    if aslist:
        val = [val]

    return val

def _extract(repo, field, target_dict, target_field, unescape=False, lower=False, cast=None, aslist=False, append=False, prepend=None, valuefunction=None):
    el = repo.find(NS + field)
    if el is not None:
        val = el.text
        if val is not None:
            val = _normalise_value(val, unescape=unescape, lower=lower, cast=cast, aslist=aslist, prepend=prepend, valuefunction=valuefunction)
            if val is None:
                return

            if append:
                target_dict[target_field] += val
            else:
                target_dict[target_field] = val

def _list_extract(repo, field, target_list, target_field=None, object_template=None, unescape=False, lower=False, cast=None, aslist=False, prepend=None, valuefunction=None):
    el = repo.find(NS + field)
    if el is not None:
        items = el.findall(NS + "item")
        for item in items:
            if object_template:
                thedict = deepcopy(object_template)
                val = item.text
                if val is not None:
                    val = _normalise_value(val, unescape=unescape, lower=lower, cast=cast, aslist=aslist, prepend=prepend, valuefunction=valuefunction)
                    if val is None:
                        return
                    thedict[target_field] = val
                    target_list.append(thedict)
            else:
                val = item.text
                if val is not None:
                    val = _normalise_value(val, unescape=unescape, lower=lower, cast=cast, aslist=aslist, prepend=prepend, valuefunction=valuefunction)
                    if val is None:
                        return
                    target_list.append(val)


def xwalk(repo):
    # the various components we need to assemble
    roar = {}
    metadata = {}
    organisations = []
    contact = {}
    oaipmh = []
    sword = {}
    rss = {}
    register = {}
    software = {}
    subjects = []
    stats = []

    # roar id
    _extract(repo, "eprintid", roar, "roar_id")

    # datestamp = date deposited
    _extract(repo, "datestamp", roar, "date_deposited", valuefunction=_normalise_date)

    # lastmod = last modified
    _extract(repo, "lastmod", roar, "last_modified", valuefunction=_normalise_date)

    # type = repository type and/or content type and/or operational status
    _extract(repo, "type", roar, "roar_type")
    _extract(repo, "type", metadata, "repository_type", aslist=True, valuefunction=_extract_repo_type)
    _extract(repo, "type", metadata, "content_type", aslist=True, valuefunction=_extract_content_type)
    _extract(repo, "type", register, "operational_status", valuefunction=_extract_status)

    # latitude = latitude of primary contact
    _extract(repo, "latitude", contact, "lat", cast=float)

    # longitude = longitude of primary contact
    _extract(repo, "longitude", contact, "lon", cast=float)

    # home_page = repository url
    _extract(repo, "home_page", metadata, "url")

    # title = repo name
    _extract(repo, "title", metadata, "name")

    # oai_pmh = oai pmh base url
    _list_extract(repo, "oai_pmh", oaipmh, "base_url", {"api_type" : "oai-pmh"})

    # sword_endpoint = sword service document url
    _extract(repo, "sword_endpoint", sword, "base_url")
    if len(sword.keys()) > 0:
        sword["api_type"] = "sword"

    # rss_feed = rss feed!
    _extract(repo, "rss_feed", rss, "base_url")
    if len(rss.keys()) > 0:
        sword["api_type"] = "rss"

    # twitter_feed = twitter
    _extract(repo, "twitter_feed", metadata, "twitter")

    # description = description
    _extract(repo, "description", metadata, "description")

    # fulltext = roar admin data, 75%+ fulltext
    _extract(repo, "fulltext", roar, "fulltext")

    # open_acces = roar admin data, 75%+ open access
    _extract(repo, "open_access", roar, "open_access")

    # mandate = roar admin data, is there an oa mandate
    _extract(repo, "mandate", roar, "mandate")

    # organisation = org name and url
    orgel = repo.find(NS + "organisation")
    if orgel is not None:
        items = orgel.findall(NS + "item")
        for item in items:
            org = {}
            titel = item.find(NS + "title")
            urlel = item.find(NS + "home_page")
            if titel is not None:
                org["name"] = titel.text
            if urlel is not None:
                org["url"] = urlel.text
            if len(org.keys()) > 0:
                organisations.append(org)

    # location = org country, + contact's city and lat/lon
    locel = repo.find(NS + "location")
    if locel is not None:
        items = locel.findall(NS + "item")
        for item in items:
            cc = item.find(NS + "country")
            lat = item.find(NS + "latitude")
            lon = item.find(NS + "longitude")
            for org in organisations:
                if cc is not None:
                    org["country_code"] = cc.text
                    metadata["country_code"] = cc.text
                if lat is not None:
                    org["lat"] = float(lat.text)
                if lon is not None:
                    org["lon"] = float(lon.text)

    # software = software name
    _extract(repo, "software", software, "name")

    # version = software version
    _extract(repo, "version", software, "version")

    # subjects = roar subject code
    _list_extract(repo, "subjects", subjects)
    if len(subjects) > 0:
        roar["subjects"] = subjects

    # contact_email = contact email!
    _extract(repo, "contact_email", contact, "email")

    # now assemble the object
    register["metadata"] = [
        {
            "lang" : "en",
            "default" : True,
            "record" : metadata
        }
    ]

    if len(software.keys()) > 0:
        register["software"] = [software]
    if len(contact.keys()) > 0:
        register["contact"] = [{"details" : contact, "role" : ["Administrator"]}]
    if len(organisations) > 0:
        register["organisation"] = [{"details" : org, "role" : ["host"]} for org in organisations]

    apis = []
    if len(oaipmh) > 0:
        apis += oaipmh
    if len(sword.keys()) > 0:
        apis += [sword]
    if len(rss.keys()) > 0:
        apis += [rss]
    if len(apis) > 0:
        register["api"] = apis

    record = {
        "register" : register,
        "admin" : {
            "roar2doar" : roar
        }
    }
    reg = oarr.Register(record)

    rh = repo.find(NS + "recordhistory")
    if rh is not None:
        history = rh.text
        counts = [int(h) for h in history.split(",")]
        lm = roar.get("last_modified")
        dt = datetime.strptime(lm, "%Y-%m-%dT%H:%M:%SZ")
        for i in range(len(counts) - 1, -1, -1):
            if counts[i] == 0:
                break
            offset = len(counts) - i - 1
            thisyear = dt - timedelta(days=offset * 365)
            thedate = thisyear.strftime("%Y-%m-%d")
            stat = {"value" :  counts[i], "type" : "item_count", "date" : thedate}
            stats.append(stat)

    return reg, stats

def run():
    rawlist = app.config.get("RAWLIST")
    resp = requests.get(rawlist)
    xml = etree.fromstring(resp.text[39:]) # have to omit the encoding for reasons known only to lxml
    repositories = xml.findall(".//" + NS + "eprint")
    limit = 4000
    i = 0
    client = oarr.OARRClient(app.config.get("OARR_BASE_URL"), app.config.get("OARR_API_KEY"))
    for repo in repositories:
        reg, stats = xwalk(repo)
        print reg.raw
        record_id = client.save_record(reg.raw)
        print stats
        for stat in stats:
            client.save_statistic(stat, record_id)

        if i >= limit: break
        i += 1


if __name__ == "__main__":
    run()