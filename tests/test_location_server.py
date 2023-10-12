from unittest import TestCase
from unittest.mock import patch
from unittest.mock import mock_open

from fastapi.testclient import TestClient

from location_server import app
from location_server import Location
from location_server import update_sherlock_state

mock_gps_current = {
    'mode': 2,
    'lat': 12.345,
    'lon': 67.890,
    'speed': 50,
    'track': 0,
    'climb': 0,
    'alt': 1000
}


class MockLocation:
    def __init__(self):
        self.city = 'Gojradia',
        self.state = 'NY'
        self.county = 'Latveria'


class TestLocationServer(TestCase):
    def setUp(self):

        self.client = TestClient(app)

        self.location = Location(mode=mock_gps_current['mode'],
                                 lat=mock_gps_current['lat'],
                                 lon=mock_gps_current['lon'],
                                 speed=mock_gps_current['speed'],
                                 track=mock_gps_current['track'],
                                 climb=mock_gps_current['climb'],
                                 alt=mock_gps_current['alt'])

        self.mock_file = mock_open(read_data='NY')

        self.file_patcher = patch('builtins.open',
                                  self.mock_file)
        self.mock_open = self.file_patcher.start()

    def tearDown(self):
        self.file_patcher.stop()

        app.current_location = None
        app.interval = 1
        app.interval_limit = 300
        app.counter = 0
        app.current_state = 'NY'

    def test_location(self):
        response = self.client.get('/location').json()

        self.assertEqual(response, None)

    def test_location_with_polling(self):
        self.client.put('/location',
                        json=mock_gps_current)

        response = self.client.get('/location').json()

        self.assertEqual(response['mode'],
                         mock_gps_current['mode'])

    @patch('location_server.update_sherlock_state')
    def test_interval_limit_exceeded(self, mock_update):
        mock_update.return_value = MockLocation()

        app.interval_limit = 1

        self.client.put('/location',
                        json=mock_gps_current)
        self.client.put('/location',
                        json=mock_gps_current)

        mock_update.assert_called_once_with(self.location)

    @patch('location_server.write_sherlock_state_and_refresh')
    @patch('location_server.geocoder.google')
    def test_update_sherlock_state(self, mock_google, mock_refresh):
        mock_google.return_value = MockLocation()

        result = update_sherlock_state(self.location)

        self.assertEqual(result.state, 'NY')
        assert not mock_refresh.called

    @patch('location_server.geocoder.google')
    def test_update_sherlock_state_google_error(self, mock_google):
        mock_google.side_effect = Exception("Whoopsie!")

        result = update_sherlock_state(self.location)
        self.assertIsNone(result)

    @patch('location_server.geocoder.google')
    def test_update_sherlock_state_writing_state(self, mock_google):
        mock_google.return_value = MockLocation()

        app.current_state = 'CT'

        result = update_sherlock_state(self.location)

        self.assertEqual(result.state, 'NY')
        self.assertEqual(app.current_state, 'NY')
        self.mock_file().write.assert_called_with('NY')

    @patch('subprocess.call')
    @patch('location_server.geocoder.google')
    def test_update_sherlock_state_file_error(self,
                                              mock_google,
                                              mock_subprocess):
        location = MockLocation()
        app.current_state = 'CT'

        mock_google.return_value = location
        mock_subprocess.return_value = None
        self.mock_open.side_effect = Exception("Whoopsie!")

        result = update_sherlock_state(self.location)
        self.assertEqual(result, location)
        mock_subprocess.assert_called_with(['./press_shortcut.sh',
                                           'F5',
                                           'Mozilla'])

        response = self.client.get('/state').json()
        self.assertEqual(response['current_state'], 'NY')

    @patch('subprocess.call')
    @patch('location_server.geocoder.google')
    def test_update_sherlock_state_window_error(self,
                                                mock_google,
                                                mock_subprocess):
        location = MockLocation()
        app.current_state = 'CT'

        mock_google.return_value = location
        mock_subprocess.side_effect = Exception("Whoopsie!")
        self.mock_open.side_effect = Exception("Whoopsie!")

        result = update_sherlock_state(self.location)
        self.assertEqual(result, location)
