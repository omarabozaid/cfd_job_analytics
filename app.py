import time
import pandas as pd
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse

class JobScraper:
    def __init__(self):
        self.driver = self.initialize_driver()
        self.scraped_jobs = set()  # Set to store scraped job identifiers

    def initialize_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(options=options)
        return driver

    def get_job_details(self, job_card):
        job_details = {}

        try:
            title = job_card.find_element(By.CLASS_NAME, 'base-search-card__title')
            job_details['post_name'] = title.text.strip()
        except:
            job_details['post_name'] = 'N/A'

        try:
            company = job_card.find_element(By.CLASS_NAME, 'base-search-card__subtitle')
            job_details['company'] = company.text.strip()
        except:
            job_details['company'] = 'N/A'

        try:
            date_posted = job_card.find_element(By.CSS_SELECTOR, 'time')
            job_details['date_posted'] = date_posted.get_attribute('datetime')
        except:
            job_details['date_posted'] = 'N/A'

        try:
            job_link = job_card.find_element(By.CSS_SELECTOR, 'a')
            job_details['link'] = job_link.get_attribute('href')
        except:
            job_details['link'] = 'N/A'

        return job_details

    def scrape_jobs(self, url_template, max_pages):
        jobs = []
        reposted_jobs = defaultdict(lambda: {'count': 0, 'dates': []})

        page_num = 0
        while page_num < max_pages:
            url = url_template + f"&start={page_num * 25}"
            print(f"Scraping page {page_num}...")
            page_num += 1
            self.driver.get(url)

            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'job-search-card'))
                )

                job_cards = self.driver.find_elements(By.CLASS_NAME, 'job-search-card')

                if not job_cards:
                    print(f"No more jobs found on page {page_num}. Stopping.")
                    break

                for job_card in job_cards:
                    job_details = self.get_job_details(job_card)

                    # Check for duplicates based on post name and date
                    if self.is_duplicate(job_details):
                        continue  # Skip duplicate job postings

                    jobs.append(job_details)
                    self.scraped_jobs.add(self.get_job_identifier(job_details))  # Add job identifier to set

                    key = (job_details['company'], job_details['date_posted'])
                    reposted_jobs[key]['count'] += 1
                    reposted_jobs[key]['dates'].append(job_details['date_posted'])

                time.sleep(3)  # Optional: Add a small delay before fetching next page
            except Exception as e:
                print(f"Error scraping page {page_num}: {str(e)}")
                break

        return jobs, reposted_jobs

    def is_duplicate(self, job_details):
        """Check if the given job details have already been scraped."""
        job_identifier = self.get_job_identifier(job_details)
        return job_identifier in self.scraped_jobs

    def get_job_identifier(self, job_details):
        """Generate a unique identifier for the job based on post name and date."""
        return (job_details['post_name'], job_details['date_posted'])

    def save_to_csv(self, jobs, filename):
        df = pd.DataFrame(jobs)
        df.to_csv(filename, index=False, encoding='utf-8-sig')  # Use UTF-8 encoding with BOM for French support

    def plot_company_post_counts(self, jobs):
        company_counts = defaultdict(int)
        for job in jobs:
            company_counts[job['company']] += 1

        sorted_counts = dict(sorted(company_counts.items(), key=lambda item: item[1], reverse=True))
        companies = list(sorted_counts.keys())
        counts = list(sorted_counts.values())

        plt.figure(figsize=(12, 6))
        plt.bar(companies[:10], counts[:10])
        plt.xlabel('Company')
        plt.ylabel('Number of Posts')
        plt.title('Top 10 Companies by Number of Job Posts')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()

    def plot_company_posts_per_month(self, reposted_jobs):
        company_month_counts = defaultdict(lambda: defaultdict(int))

        for key, value in reposted_jobs.items():
            company = key[0]
            dates = value['dates']
            month_counts = defaultdict(int)

            for date in dates:
                month = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m')
                month_counts[month] += 1

            company_month_counts[company] = dict(month_counts)

        plt.figure(figsize=(12, 8))
        for company, month_counts in company_month_counts.items():
            months = list(month_counts.keys())
            counts = list(month_counts.values())
            plt.plot(months, counts, label=company, marker='o')

        plt.xlabel('Month')
        plt.ylabel('Number of Posts')
        plt.title('Company Job Posts per Month')
        plt.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()

    def close_driver(self):
        self.driver.quit()


def get_time_filter():
    while True:
        print("Choose time filter:")
        print("1. Last 24 hours")
        print("2. Last week")
        print("3. Last month")
        print("4. Never")
        choice = input("Enter your choice (1-4): ")

        if choice in ['1', '2', '3', '4']:
            return choice
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")


def main():
    job_scraper = JobScraper()

    # Get user input for time filter
    time_filter = get_time_filter()

    # Map user choice to LinkedIn filter
    if time_filter == '1':
        f_TPR = 'r86400'  # Last 24 hours
    elif time_filter == '2':
        f_TPR = 'r604800'  # Last week
    elif time_filter == '3':
        f_TPR = 'r2592000'  # Last month
    else:
        f_TPR = ''  # No time filter

    # Construct the URL template with chosen filters
    url_template = f"https://www.linkedin.com/jobs/search/?&f_TPR={f_TPR}&keywords=cfd&location=France&origin=JOB_SEARCH_PAGE_JOB_FILTER"

    # Get user input for maximum pages to scrape
    max_pages = int(input("Enter maximum number of pages to scrape: "))

    jobs, reposted_jobs = job_scraper.scrape_jobs(url_template, max_pages)

    job_scraper.save_to_csv(jobs, 'cfd_jobs_with_filters.csv')

    print(f"Scraped {len(jobs)} CFD job postings in France with filters. Saved to 'cfd_jobs_with_filters.csv'.")

    # Plotting
    job_scraper.plot_company_post_counts(jobs)
    job_scraper.plot_company_posts_per_month(reposted_jobs)

    job_scraper.close_driver()


if __name__ == "__main__":
    main()
