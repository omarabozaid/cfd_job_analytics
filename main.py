import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from collections import defaultdict
import re
from fuzzywuzzy import fuzz

# Define software and their keywords with potential variations
software = {
    'OpenFOAM': ['openfoam'],
    'Ansys': ['ansys', 'fluent', 'star-ccm', 'starccm', 'starccm+', 'star ccm', 'starccmplus'],
    'Abaqus': ['abaqus'],
    'Calculix': ['calculix'],
    'FreeFEM+': ['freefem+'],
    'Fluent': ['fluent', 'ansys fluent'],
    'Star-CCM+': ['starccm', 'star-ccm', 'star ccm', 'starccm+']
}

domains = {
    'aerodynamics': ['aerodynamic', 'aerodynamics', 'aérodynamique'],
    'hydrodynamics': ['hydrodynamic', 'hydrodynamics', 'hydrodynamique', 'ocean', 'oceanic', 'oceanique'],
    'combustion': ['combustion', 'reactive', 'reaction', 'cryogenic'],
    'rotating equipment': ['rotating', 'équipement tournant'],
    'mooring': ['mooring', 'amarrage'],
    'naval architect': ['naval architect', 'architecte naval'],
    'fluid dynamics': ['fluid dynamics', 'dynamique des fluides'],
    'heat transfer': ['heat transfer', 'transfert de chaleur'],
    'renewable energy': ['renewable energy', 'énergie renouvelable'],
    'environmental modelling': ['environmental modelling', 'modélisation environnementale']
}

applications = {
    'aircraft': ['aircraft', 'drones', 'flights'],
    'ships/vessels': ['ships', 'vessels', 'piping', 'oil and gas'],
    'engines': ['engines', 'moteurs'],
    'turbines/compressors': ['turbines', 'compressors']
}

languages = {
    'python': ['python'],
    'c++': ['c++', 'cpp'],
    'matlab': ['matlab'],
    'english': ['english', 'anglais'],
    'french': ['french', 'français']
}

def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)
    return driver

def get_job_details(job_card):
    job_details = {}
    
    try:
        title = job_card.find_element(By.CLASS_NAME, 'base-search-card__title')
        job_details['title'] = title.text.strip()
    except:
        job_details['title'] = 'N/A'
    
    try:
        company = job_card.find_element(By.CLASS_NAME, 'base-search-card__subtitle')
        job_details['company'] = company.text.strip()
    except:
        job_details['company'] = 'N/A'
    
    try:
        location = job_card.find_element(By.CLASS_NAME, 'job-search-card__location')
        job_details['location'] = location.text.strip()
    except:
        job_details['location'] = 'N/A'
    
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
    
    try:
        description = job_card.find_element(By.CLASS_NAME, 'job-search-card__snippet')
        job_details['description'] = description.text.strip()
    except:
        job_details['description'] = 'N/A'
    
    return job_details

def scrape_jobs(url, start_date, end_date):
    driver = initialize_driver()
    driver.get(url)
    
    jobs = []
    reposted_jobs = defaultdict(lambda: {'count': 0, 'dates': []})
    
    while True:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'job-search-card'))
            )

            job_cards = driver.find_elements(By.CLASS_NAME, 'job-search-card')
            
            for job_card in job_cards:
                job_details = get_job_details(job_card)
                job_date = job_details['date_posted']
                
                if job_date != 'N/A':
                    job_date = datetime.strptime(job_date, '%Y-%m-%d')
                    if start_date <= job_date <= end_date:
                        jobs.append(job_details)
                        
                        # Track reposted jobs
                        key = (job_details['title'], job_details['company'], job_details['location'])
                        reposted_jobs[key]['count'] += 1
                        reposted_jobs[key]['dates'].append(job_date)
            
            # Try to click the 'next' button to go to the next page of results
            next_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Next"]')
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
        except Exception as e:
            print("No more pages or error:", e)
            break
    
    driver.quit()
    return jobs, reposted_jobs

def classify_job_details(job):
    title_lower = job['title'].lower()
    company_lower = job['company'].lower()
    description_lower = job.get('description', '').lower()

    # Domain classification 
    for domain, keywords in domains.items():
        for keyword in keywords:
            if keyword in description_lower:
                job['domain'] = domain
                break
        else:
            continue
        break
    else:
        job['domain'] = 'other'

    # Application classification 
    for application, keywords in applications.items():
        for keyword in keywords:
            if keyword in description_lower:
                job['application'] = application
                break
        else:
            continue
        break
    else:
        job['application'] = 'other'

    # Software classification with fuzzy matching
    for software_name, keywords in software.items():
        software_found = False
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower):
                job[software_name] = 1  # Indicates software mentioned
                software_found = True
                break
            elif fuzz.partial_ratio(keyword, description_lower) >= 90:
                job[software_name] = 1  # Indicates software mentioned (fuzzy match)
                software_found = True
                break
        if not software_found:
            job[software_name] = 0  # Indicates software not mentioned

    # Language classification 
    for language, keywords in languages.items():
        for keyword in keywords:
            if keyword in description_lower:
                job[language] = 1
                break
        else:
            job[language] = 0

    return job

def save_to_csv(jobs, filename):
    df = pd.DataFrame(jobs)
    df.to_csv(filename, index=False, encoding='utf-8-sig')  # Use UTF-8 encoding with BOM for French support

def main():
    url = "https://www.linkedin.com/jobs/search/?keywords=cfd&location=France"
    start_date = datetime.now() - timedelta(days=60)  # Last 60 days
    end_date = datetime.now()
    
    jobs, reposted_jobs = scrape_jobs(url, start_date, end_date)
    
    classified_jobs = [classify_job_details(job) for job in jobs]
    
    save_to_csv(classified_jobs, 'cfd_jobs.csv')

    print(f"Scraped and classified {len(jobs)} CFD jobs in France. Saved to 'cfd_jobs.csv'.")
    
    # Print reposted jobs
    for job, details in reposted_jobs.items():
        print(f"Job: {job}, Reposted: {details['count']} times, Dates: {details['dates']}")

if __name__ == "__main__":
    main()
