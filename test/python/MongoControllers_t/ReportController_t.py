#!/usr/bin/env python
"""
_ReportController_t_
Unit test for ReportController helper class.
"""

import unittest
from pymongo.collection import Collection

from Databases.Mongo.MongoClient import MongoClient
from MongoControllers.ReportController import ReportController


class MockMongoClient(MongoClient):
    def _setMongoCollection(self) -> Collection:
        return self.client.unified.reportInfo

    def _buildMongoDocument(self) -> None:
        pass


class ReportControllerTest(unittest.TestCase):
    mongoSettings = {"database": "unified", "collection": "reportInfo"}

    # The data in ReportInfo is always changing.
    # For now, test the get method with a workflow got randomly from mongo.
    mockMongoClient = MockMongoClient()
    params = {"workflow": mockMongoClient._getOne()["workflow"], "dropKey": "_id", "dateTimeKeys": ["time", "date"]}

    def setUp(self) -> None:
        self.reportController = ReportController()
        super().setUp()
        return

    def tearDown(self) -> None:
        super().tearDown()
        return

    def testMongoSettings(self):
        """MongoClient gets the connection to MongoDB"""
        isCollection = isinstance(self.reportController.collection, Collection)
        self.assertTrue(isCollection)

        rightName = self.reportController.collection.database.name == self.mongoSettings.get("database")
        self.assertTrue(rightName)

        rightName = self.reportController.collection.name == self.mongoSettings.get("collection")
        self.assertTrue(rightName)

    def testGet(self):
        """get gets the report info for a given workflow"""
        # Test when the workflow exists
        result = self.reportController.get(self.params.get("workflow"))
        isDict = isinstance(result, dict)
        self.assertTrue(isDict)

        noDropKey = self.params.get("dropKey") not in result
        self.assertTrue(noDropKey)

        hasDateTimeKeys = all(k in result for k in self.params.get("dateTimeKeys"))
        self.assertTrue(hasDateTimeKeys)

        # Test when the worklfow does not exist
        result = self.reportController.get("test")
        isNone = result is None
        self.assertTrue(isNone)


if __name__ == "__main__":
    unittest.main()
