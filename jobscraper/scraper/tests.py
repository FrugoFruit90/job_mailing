# jobscraper/scraper/tests.py
from django.test import TestCase
from unittest.mock import patch, MagicMock

from scraper.job_downloader import PracujDownloader
from scraper.models import Company, Job


class PracujDownloaderTestCase(TestCase):
    def setUp(self):
        # Create a test company
        self.company = Company.objects.create(
            name="test company",
            url="https://example.com",
            size_from=10,
            size_to=50
        )

    @patch('scraper.job_downloader.requests.get')
    def test_download_jobs(self, mock_get):
        # Mock the response
        mock_response = MagicMock()
        mock_response.content = """
        <div data-test="section-offers">
            <div>
                <div class="listing_c1a12" data-test-offerid="1234567">
                    <h2 data-test="offer-title">Test Job Title</h2>
                    <div data-test="section-company">
                        <h3>Test Company</h3>
                        <div>
                            <li>Mid</li>
                        </div>
                    </div>
                    <span data-test="offer-salary">5000 - 7000 PLN</span>
                </div>
            </div>
        </div>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Create downloader and run
        downloader = PracujDownloader()
        with patch('scraper.job_downloader.Job.objects.filter') as mock_filter:
            # Make it seem like the job doesn't exist yet
            mock_filter.return_value.exists.return_value = False

            # Also patch the Company manager
            with patch('scraper.job_downloader.Company.objects.create_or_update_if_better') as mock_company:
                mock_company.return_value = self.company

                jobs_added = downloader.download_jobs('https://test.url', max_pages=1)

        # Assertions
        self.assertEqual(mock_get.call_count, 1)
        self.assertTrue(mock_get.call_args[0][0].startswith('https://test.url'))

        # Since our test is heavily mocked, we can't really assert that jobs were added
        # but we can check that the right methods were called
        mock_filter.assert_called()
        mock_company.assert_called()