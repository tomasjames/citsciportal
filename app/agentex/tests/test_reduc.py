# Import TestCase from unittest 
from django.test import TestCase, Client

# Import reverse
from django.core.urlresolvers import reverse

# Import Mock to allow for function calls
from mock import Mock, patch

# Import view required
from agentex.datareduc import *
from agentex.views import *
from agentex.models import *

'''
Actual tests live here.


class TestCalibratorData(TestCase):
    
    '''
    This tests the function calibrator_data from datareduc.py
    '''
    
    def test_calibrator_data(self):

        calid = 1.
        code = 'corot2b'
        return_collection = calibrator_data(calid,code)
        data = return_collection[0]
        time = return_collection[1]
        people = return_collection[2]
        
        self.assertIsNotNone(data)

class TestAverageCombine(TestCase):

    def setUp(self):
        self.client = Client()

    def test_average_combine(self):


class TestPhotometry(TestCase):
    
    @patch('agentex.datareduc.calibrator_averages', side_effect=mocking_calave)
    
    def test_photometry(self, mocking_calave):

        photom = photometry(code=0,person=None)
        cal_ave = mocking_calave()
 
        self.assertNotEqual(cal_ave, photom)
'''