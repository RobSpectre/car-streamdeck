from datetime import datetime

import unittest
from unittest.mock import patch
from unittest.mock import mock_open 
from unittest.mock import call 

from io import StringIO

from send_sherlock_report import (
    get_location,
    get_gps_coordinates,
    get_address,
    get_data_logs,
    write_data_logs
)

now = datetime.now()
now_string = now.strftime("time %I:%M:%S%p date %Y/%m/%d")

class MockGPSCurrent:
    def __init__(self):
        self.lat = 12.345
        self.lon = 67.890
        self.alt = 100
        self.mode = 2

    def speed(self):
        return 50

    def position(self):
        return (self.lat, self.lon)

class MockGPSCurrentNoFix:
    def __init__(self):
        self.mode = 1

class MockLocation:
    def __init__(self):
        self.city = 'Sample City',
        self.state = 'Sample State'
        self.county = 'Sample County'


class TestSendSherlockReport(unittest.TestCase):
    @patch('send_sherlock_report.get_address')
    @patch('send_sherlock_report.get_gps_coordinates')
    def test_get_location_with_gps_data(self,
                                        mock_get_gps_coordinates,
                                        mock_get_address):
        # Mock the get_gps_coordinates function to return dummy data
        mock_get_gps_coordinates.return_value = MockGPSCurrent() 
        mock_get_address.return_value = MockLocation() 
        
        location = get_location()
        self.assertIsNotNone(location)
        self.assertEqual(location['lat'], 12.345)
        self.assertEqual(location['lon'], 67.890)
        self.assertEqual(location['speed'], 50)

    @patch('send_sherlock_report.get_gps_coordinates')
    def test_get_location_without_gps_data(self, mock_get_gps_coordinates):
        # Mock the get_gps_coordinates function to return None
        mock_get_gps_coordinates.return_value = None
        
        location = get_location()
        self.assertIsNone(location)

    @patch('send_sherlock_report.gpsd.connect')
    def test_get_gps_coordinates_without_gpsd(self, mock_gpsd_connect):
        # Mock the get_gps_coordinates function to return None
        mock_gpsd_connect.side_effect = Exception("Whoopsie!")
        
        location = get_gps_coordinates()
        self.assertIsNone(location)

    @patch('send_sherlock_report.get_address')
    @patch('send_sherlock_report.get_gps_coordinates')
    def test_get_location_without_address(self,
                                          mock_get_gps_coordinates,
                                          mock_get_address):
        # Mock the get_gps_coordinates function to return None
        mock_get_gps_coordinates.return_value = MockGPSCurrent() 
        mock_get_address.return_value = None
        
        location = get_location()
        self.assertIsNone(location)

    @patch('send_sherlock_report.gpsd.connect')
    def test_get_gps_coordinates_with_fix(self, mock_gpsd_connect):
        # Mock the gpsd.connect function to succeed
        mock_gpsd_connect.return_value = True
        
        with patch('send_sherlock_report.gpsd.get_current') as mock_get_current:
            # Mock the gpsd.get_current function to return dummy data
            mock_get_current.return_value = MockGPSCurrent() 
            
            current = get_gps_coordinates()
            self.assertIsNotNone(current)
            self.assertEqual(current.lat, 12.345)
            self.assertEqual(current.lon, 67.890)

    @patch('send_sherlock_report.gpsd.connect')
    def test_get_gps_coordinates_without_fix(self, mock_gpsd_connect):
        # Mock the gpsd.connect function to succeed
        mock_gpsd_connect.return_value = True
        
        with patch('send_sherlock_report.gpsd.get_current') as mock_get_current:
            # Mock the gpsd.get_current function to return dummy data without a fix
            mock_get_current.return_value = MockGPSCurrentNoFix()

            current = get_gps_coordinates()
            self.assertIsNone(current)

    @patch('send_sherlock_report.geocoder.google')
    def test_get_address_with_data(self, mock_geocoder_google):
        # Mock the geocoder.google function to return dummy data
        mock_geocoder_google.return_value = {
            'city': 'Sample City',
            'county': 'Sample County',
            'state': 'Sample State',
        }
        
        address = get_address(MockGPSCurrent())
        self.assertIsNotNone(address)
        self.assertEqual(address['city'], 'Sample City')
        self.assertEqual(address['county'], 'Sample County')
        self.assertEqual(address['state'], 'Sample State')

    @patch('send_sherlock_report.geocoder.google')
    def test_get_address_without_data(self, mock_geocoder_google):
        # Mock the geocoder.google function to return None
        mock_geocoder_google.return_value = None
        
        address = get_address(MockGPSCurrentNoFix)
        self.assertIsNone(address)

    @patch('builtins.open', new_callable=unittest.mock.mock_open,
           read_data=f'Sample Data {now_string}\n')
    def test_get_data_logs(self, mock_open):
        lines = get_data_logs()
        self.assertEqual(lines, [f'Sample Data {now_string}\n'])

    @patch('builtins.open', new_callable=mock_open)
    def test_write_data_logs(self, mock_file):
        # Input data for testing
        agency = "Agency"
        location = "Baker Street"
        lines = ["line1", "line2", "line3"]

        # Expected JSON strings
        expected_json = [
            '{"agency": "Agency", "location": "Baker Street", "data": "line1"}\n',
            '{"agency": "Agency", "location": "Baker Street", "data": "line2"}\n',
            '{"agency": "Agency", "location": "Baker Street", "data": "line3"}\n',
        ]

        # Execute the function
        write_data_logs(agency, location, lines)

        # Verify that the mock file was called with the expected data
        mock_file.assert_called_once_with("sherlock.jsonl", "a")

        expected_calls = [call(expected_json[0]),
                          call(expected_json[1]),
                          call(expected_json[2])]
        mock_file().write.assert_has_calls(expected_calls, any_order=False)
