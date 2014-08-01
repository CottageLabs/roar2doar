import requests, HTMLParser
from lxml import etree
from datetime import datetime, timedelta
from copy import deepcopy
from roar2doar.core import app
from roar2doar import oarr

NS = "{http://eprints.org/ep2/data/2.0}"
APP_NAME = app.config.get("OARR_APP_NAME")

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

def get_stats(repo):
    # first get the last modified date of this record, so we have a place to measure our stats from
    lm = repo.find(NS + "lastmod")
    if lm is None:
        return False
    nd = _normalise_date(lm.text)
    dt = datetime.strptime(nd, "%Y-%m-%dT%H:%M:%SZ")

    # get the current record count
    current_stat = None
    rc = repo.find(NS + "recordcount")
    if rc is not None and rc.text is not None:
        count = int(rc.text)
        current_stat = {"value" : count, "type" : "item_count", "date" : nd}

    # extract the historical stats from the recordhistory elemenet.  We assume that each
    # entry is in increments of 1 year back from the last updated date.  This is probably not
    # strictly true, but in the absence of better information ...
    old_stats = []
    rh = repo.find(NS + "recordhistory")
    if rh is not None:
        history = rh.text
        counts = [int(h) for h in history.split(",")]
        for i in range(len(counts) - 1, -1, -1):
            if counts[i] == 0:
                break
            offset = len(counts) - i - 1
            thisyear = dt - timedelta(days=offset * 365)
            thedate = thisyear.strftime("%Y-%m-%d")
            stat = {"value" :  counts[i], "type" : "item_count", "date" : thedate}
            old_stats.append(stat)

    return old_stats, current_stat

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
            APP_NAME : roar
        }
    }
    reg = oarr.Register(record)

    return reg

def _do_md_patch(original, new, field, append_list=False, doar_over_roar=True):
    oval = original.get_metadata_value(field)
    nval = new.get_metadata_value(field)

    if append_list:
        if oval is not None and nval is not None:
            pval = list(set(oval + nval))
            original.set_metadata_value(field, pval)
        elif oval is None and nval is not None:
            original.set_metadata_value(field, deepcopy(nval))
    elif doar_over_roar:
        if oval is None and nval is not None:
            original.set_metadata_value(field, nval)

def _do_api_patch(original, new, api_type):
    cbases = [a.get("base_url") for a in original.get_api(api_type) if a.get("base_url") is not None]
    napis = new.get_api(api_type)
    for napi in napis:
        nbase = napi.get("base_url")
        if nbase in cbases:
            continue
        original.add_api_object(deepcopy(napi))

def patch(original, new):
    # repository_type -> append to list (deduplicated)
    _do_md_patch(original, new, "repository_type", append_list=True)

    # content_type -> append to list (deduplicated)
    _do_md_patch(original, new, "content_type", append_list=True)

    # operational_status -> prefer doar over roar
    if original.operational_status is None and new.operational_status is not None:
        original.operational_status = new.operational_status

    # contacts -> keep the contact if their email is not already know, else discard
    oemails = [c.get("details", {}).get("email") for c in original.contact if c.get("details", {}).get("email") is not None]
    ncontacts = new.contact
    for ncont in ncontacts:
        nemail = ncont.get("details", {}).get("email")
        if nemail is not None and nemail in oemails:
            continue
        original.add_contact_object(deepcopy(ncont))

    # name -> prefer doar over roar
    if original.repo_name is None and new.repo_name is not None:
        original.repo_name = new.repo_name

    # oai-pmh -> keep the entry if the base url is not already known
    _do_api_patch(original, new, "oai-pmh")

    # sword -> keep the entry if the base url is not already known
    _do_api_patch(original, new, "sword")

    # rss -> keep the entry if the base url is not already known
    _do_api_patch(original, new, "rss")

    # twitter -> prefer doar over roar
    _do_md_patch(original, new, "twitter")

    # description -> prefer doar over roar
    _do_md_patch(original, new, "description")

    # organisation -> keep the org if their url is not already known, else discard
    ourls = [o.get("details", {}).get("url") for o in original.organisation if o.get("details", {}).get("url") is not None]
    ourlvars = []
    for ourl in ourls:
        vars = oarr.OARRClient.make_url_variants(ourl)
        ourlvars += vars
    ourlvars = list(set(ourlvars))

    norgs = new.organisation
    for norg in norgs:
        nurl = norg.get("details", {}).get("url")
        if nurl is not None and nurl in ourlvars:
            continue
        original.add_organisation_object(deepcopy(norg))

    # country_code -> prefer doar over roar
    if original.country_code is None and new.country_code is not None:
        original.set_country(code=new.country_code)

    # software -> if (normalised) name different keep, else discard
    onames = [name.strip().lower() for name, version, url in original.software if name is not None]
    nsoft = new.software
    for nname, nver, nurl in nsoft:
        if nname is not None:
            if nname.strip().lower() in onames:
                continue
            original.add_software(nname, nver, nurl)

def should_update(repo, client):
    lm = repo.find(NS + "lastmod")
    hp = repo.find(NS + "home_page")

    if lm is None or hp is None:
        return False, None

    nd = _normalise_date(lm.text)
    dt = datetime.strptime(nd, "%Y-%m-%dT%H:%M:%SZ")

    url = hp.text
    reg = client.get_by_url(url)

    if reg is None:
        return True, None

    r2d = reg.get_admin(app.config.get("OARR_APP_NAME"))
    if r2d is None:
        return True, reg

    r2dlm = r2d.get("last_modified")
    if r2dlm is None:
        return True, reg

    rdt = datetime.strptime(reg.last_updated, "%Y-%m-%dT%H:%M:%SZ")
    if rdt < dt:
        return True, reg

    return False, None


def run():
    # pull everything in from the rawlist and load the xml
    rawlist = app.config.get("RAWLIST")
    resp = requests.get(rawlist)
    xml = etree.fromstring(resp.text[39:]) # have to omit the encoding for reasons known only to lxml
    repositories = xml.findall(".//" + NS + "eprint")

    # create an instance of the client for OARR for re-use
    client = oarr.OARRClient(app.config.get("OARR_BASE_URL"), app.config.get("OARR_API_KEY"))

    for repo in repositories:
        # decide if we are going to try to import this record at all
        should, existing = should_update(repo, client)
        if not should:
            print "repository has not been updated since last run - skipping"
            continue

        # if we get to here, we want to do the xwalk, so do the registry data first
        reg = xwalk(repo)
        print reg.raw

        # if there's no repo url, then we don't bother to go any further
        if reg.repo_url is None or reg.repo_url == "":
            print "No Repository URL - skipping"
            continue

        # record_id may be None, or it may exist if there is already a record for this url
        record_id = None
        if existing is not None:
            print "updating ", existing.id
            patch(existing, reg)
            existing.set_admin_object(APP_NAME, reg.get_admin(APP_NAME))
            record_id = existing.id
            reg = existing

        # save the new or patched record (record_id may still be None)
        record_id = client.save_record(reg.raw, record_id)

        if record_id is not None and not record_id:
            print "error saving"
            break

        historical_stats, current_stat = get_stats(repo)
        if existing is not None:
            # add the new stat
            print current_stat
            client.save_statistic(current_stat, record_id)
        else:
            # add the historic stats
            print historical_stats
            for stat in historical_stats:
                client.save_statistic(stat, record_id)


if __name__ == "__main__":
    run()