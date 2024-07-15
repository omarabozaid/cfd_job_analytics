import csv
from job_scraper import JobScraper  # Assuming you have a JobScraper class defined in job_scraper.py

def main():
    job_scraper = JobScraper()

    # Define filters
    time_filters = {
        #'1': 'r86400',  # Last 24 hours
        #'2': 'r604800',  # Last week
        #'3': 'r2592000',  # Last month
        '4': ''  # All time
    }

    countries = {
        '1': 'France',
        '2': 'United Kingdom',
        '3': 'United States',
        '4': 'Germany'
    }

    # Get user input for maximum pages to scrape
    max_pages = 50

    results = []

    for time_key, f_TPR in time_filters.items():
        for country_key, location in countries.items():
            # Construct the URL template with chosen filters
            url_template = f"https://www.linkedin.com/jobs/search/?&f_TPR={f_TPR}&keywords=cfd&location={location}&origin=JOB_SEARCH_PAGE_JOB_FILTER"

            jobs, reposted_jobs = job_scraper.scrape_jobs(url_template, max_pages)
            
            # Collect statistics
            result = {
                'country': location,
                'time_filter': time_key,
                'n_jobs': len(jobs)
            }
            results.append(result)

            # Save individual job data to a CSV file
            job_scraper.save_to_csv(jobs, f'cfd_jobs_{location}_{time_key}.csv')

            print(f"Scraped {len(jobs)} CFD job postings in {location} with time filter {time_key}. Saved to 'cfd_jobs_{location}_{time_key}.csv'.")

            # Plotting (optional, if you need to generate plots for each iteration)
            job_scraper.plot_company_post_counts(jobs)
            job_scraper.plot_company_posts_per_month(reposted_jobs)

    job_scraper.close_driver()

    # Save aggregated statistics to a CSV file
    with open('job_statistics.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['country', 'time_filter', 'n_jobs'])
        writer.writeheader()
        writer.writerows(results)

    print("Aggregated statistics saved to 'job_statistics.csv'.")

if __name__ == "__main__":
    main()
