from unittest import TestCase
from roar2doar import oarr
from roar2doar import importer

class TestSnapshot(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_01_patch_simple(self):
        doar = oarr.Register()
        doar.add_repository_type("Institutional")
        doar.add_content_type("Theses")
        doar.operational_status = "Operational"
        doar.add_contact_object({"role" : ["Administrator"], "details" : {"name" : "Contact 1", "email" : "contact1@roar2.doar"}})
        doar.set_repo_name("My Repository")
        doar.add_api_object({"base_url" : "http://oai.1", "api_type" : "oai-pmh"})
        doar.twitter = "twitme"
        doar.description = "A great repository"
        doar.add_organisation_object({"role" : ["host"], "details" : {"name" : "org 1", "url" : "http://org.1"}})
        doar.set_country(code="gb")
        doar.add_software("DSpace", "3.1", None)

        roar = oarr.Register()
        roar.add_repository_type("Governmental")
        roar.add_content_type("Articles")
        roar.operational_status = "Trial"
        roar.add_contact_object({"role" : ["Administrator"], "details" : {"name" : "Contact 2", "email" : "contact2@roar2.doar"}})
        roar.set_repo_name("An Repository")
        roar.add_api_object({"base_url" : "http://oai.2", "api_type" : "oai-pmh"})
        roar.twitter = "tweetme"
        roar.description = "An amazing repository"
        roar.add_organisation_object({"role" : ["host"], "details" : {"name" : "org 2", "url" : "http://org.2"}})
        roar.set_country(code="fr")
        roar.add_software("EPrints", "3.3", None)

        importer.patch(doar, roar)

        assert len(doar.repository_type) == 2
        assert "Institutional" in doar.repository_type
        assert "Governmental" in doar.repository_type

        assert len(doar.content_type) == 2
        assert "Theses" in doar.content_type
        assert "Articles" in doar.content_type

        assert doar.operational_status == "Operational"

        assert len(doar.contact) == 2
        emails = [c.get("details").get("email") for c in doar.contact]
        assert "contact1@roar2.doar" in emails
        assert "contact2@roar2.doar" in emails

        assert doar.repo_name == "My Repository"

        apis = doar.get_api("oai-pmh")
        assert len(apis) == 2
        urls = [api.get("base_url") for api in apis]
        assert "http://oai.1" in urls
        assert "http://oai.2" in urls

        assert doar.twitter == "twitme"

        assert doar.description == "A great repository"

        assert len(doar.organisation) == 2
        urls = [o.get("details").get("url") for o in doar.organisation]
        assert "http://org.1" in urls
        assert "http://org.2" in urls

        assert doar.country_code == "GB"
        assert doar.country == "United Kingdom"

        assert len(doar.software) == 2
        names = [n for n, v, u in doar.software]
        assert "DSpace" in names
        assert "EPrints" in names

    def test_02_patch_complex(self):
        doar = oarr.Register()
        doar.add_repository_type("Institutional")
        doar.add_content_type("Theses")
        doar.add_contact_object({"role" : ["Administrator"], "details" : {"name" : "Contact 1", "email" : "contact1@roar2.doar"}})
        doar.add_api_object({"base_url" : "http://oai.1", "api_type" : "oai-pmh"})
        doar.add_organisation_object({"role" : ["host"], "details" : {"name" : "org 1", "url" : "http://org.1"}})

        roar = oarr.Register()
        roar.add_repository_type("Institutional")
        roar.add_repository_type("Governmental")
        roar.add_content_type("Theses")
        roar.add_content_type("Articles")
        roar.operational_status = "Trial"
        roar.add_contact_object({"role" : ["Administrator"], "details" : {"name" : "Contact 1", "email" : "contact1@roar2.doar"}})
        roar.add_contact_object({"role" : ["Administrator"], "details" : {"name" : "Contact 2", "email" : "contact2@roar2.doar"}})
        roar.set_repo_name("An Repository")
        roar.add_api_object({"base_url" : "http://oai.1", "api_type" : "oai-pmh"})
        roar.add_api_object({"base_url" : "http://oai.2", "api_type" : "oai-pmh"})
        roar.twitter = "tweetme"
        roar.description = "An amazing repository"
        roar.add_organisation_object({"role" : ["host"], "details" : {"name" : "org 1", "url" : "http://org.1/"}})
        roar.add_organisation_object({"role" : ["host"], "details" : {"name" : "org 2", "url" : "http://org.2"}})
        roar.set_country(code="fr")

        importer.patch(doar, roar)

        assert len(doar.repository_type) == 2
        assert "Institutional" in doar.repository_type
        assert "Governmental" in doar.repository_type

        assert len(doar.content_type) == 2
        assert "Theses" in doar.content_type
        assert "Articles" in doar.content_type

        assert doar.operational_status == "Trial"

        assert len(doar.contact) == 2
        emails = [c.get("details").get("email") for c in doar.contact]
        assert "contact1@roar2.doar" in emails
        assert "contact2@roar2.doar" in emails

        assert doar.repo_name == "An Repository"

        apis = doar.get_api("oai-pmh")
        assert len(apis) == 2
        urls = [api.get("base_url") for api in apis]
        assert "http://oai.1" in urls
        assert "http://oai.2" in urls

        assert doar.twitter == "tweetme"

        assert doar.description == "An amazing repository"

        assert len(doar.organisation) == 2
        urls = [o.get("details").get("url") for o in doar.organisation]
        assert "http://org.1" in urls
        assert "http://org.2" in urls

        assert doar.country_code == "FR"
        assert doar.country == "France"
