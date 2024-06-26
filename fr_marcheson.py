from gec_common.gecclass import *
import logging
from gec_common import log_config
SCRIPT_NAME = "fr_marcheson_spn"
log_config.log(SCRIPT_NAME)
import requests
import re
import os
import jsons
import time
from datetime import date, datetime, timedelta
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.common.by import By
import gec_common.OutputJSON
from gec_common import functions as fn
import xml.etree.ElementTree as ET
import gec_common.web_application_properties as application_properties
import requests
from bs4 import BeautifulSoup
import csv
 
NOTICE_DUPLICATE_COUNT = 0
MAX_NOTICES_DUPLICATE = 4
MAX_NOTICES = 2000
notice_count = 0
t_notice_count = 0
SCRIPT_NAME = "fr_marcheson_spn"
output_json_file = gec_common.OutputJSON.OutputJSON(SCRIPT_NAME)
output_json_folder = "jsonfile"
 
 
def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    global t_notice_count
    notice_data = tender()
    notice_data.script_name = 'fr_marcheson_spn'
    notice_data.main_language = 'FR'
    performance_country_data = performance_country()
    performance_country_data.performance_country = 'FR'
    notice_data.performance_country.append(performance_country_data)
    notice_data.procurement_method = 2
    notice_data.notice_type = 4
    notice_data.currency = 'EUR'
    notice_data.class_at_source = 'CPV'
    try:
        notice_data.local_title = tender_html_element['title']
        notice_data.notice_title = GoogleTranslator(source='auto', target='en').translate(notice_data.local_title)
    except Exception as e:
        logging.info("Exception in local_title: {}".format(type(e).__name__))
        pass
 
    try:  
        notice_data.publish_date = tender_html_element['pubDate']
        logging.info(notice_data.publish_date)
    except Exception as e:
        logging.info("Exception in publish_date: {}".format(type(e).__name__))
        pass
 
#     if notice_data.publish_date is not None and notice_data.publish_date < threshold:
#         return
 
    notice_data.notice_url = tender_html_element['link']    
    logging.info(notice_data.notice_url)
    
#-----------------page detils extract using request-----------------------
    time.sleep(1)
    response = requests.get(notice_data.notice_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    if response.status_code == 200:
 
 
        try:
            notice_data.contract_type_actual = soup.select_one('div.lg\:flex.mt-8.lg\:mt-6.lg\:items-center.text-secondary-base.text-m.font-medium > div:nth-child(1) > span').get_text()
            contract_type_actual = GoogleTranslator(source='auto', target='en').translate(notice_data.contract_type_actual)
            notice_contract_type = fn.procedure_mapping("assets/fr_marcheson_spn_contract_type.csv",contract_type_actual.lower())
            notice_data.notice_contract_type = notice_contract_type
        except Exception as e:
            logging.info("Exception in contract_type_actual: {}".format(type(e).__name__)) 
            pass
        
        try:
            text_data = soup.find('div', class_='overflow-auto mt-4 p-4').get_text()
            text_data_lower = text_data.lower()
            notice_data.notice_text = text_data
        except:
            pass
        
        try:
            notice_no = soup.find('div', class_='text-white text-m xl:text-l').get_text()
            notice_data.notice_no =re.sub("Avis n°","",notice_no)
        except:
            pass
        
        try:
            notice_data.type_of_procedure_actual = soup.select_one('div.lg\:flex.mt-8.lg\:mt-6.lg\:items-center.text-secondary-base.text-m.font-medium > div:nth-child(2) > span').get_text().strip()
            type_of_procedure_actual = GoogleTranslator(source='auto', target='en').translate(notice_data.type_of_procedure_actual)
            notice_data.type_of_procedure = fn.procedure_mapping('assets/fr_marcheson_procedure.csv',type_of_procedure_actual.lower())
        except Exception as e:
            logging.info("Exception in type_of_procedure_actual: {}".format(type(e).__name__))
            pass
        
        try: 
            est_amount = text_data.split('Valeur estimée hors TVA :')[1].split('\n')[0].strip()
            est_amount =re.sub("[^\d\.\,]","",est_amount)
            est_amount = est_amount.replace(',','')
            notice_data.est_amount = float(est_amount)
            notice_data.netbudgetlc = notice_data.est_amount
        except Exception as e:
            logging.info("Exception in netbudgetlc: {}".format(type(e).__name__)) 
            pass  
        
        try:
            text_data_lot = soup.find('div', class_='limit-descript-height descript-line').get_text()
            text_data_lot_lower = text_data_lot.lower()
        except:
            pass
        
        try:
            lot_number = 1  
            if "lot :  lot-00" in text_data_lower:
                lots = re.split('lot :  lot-00',text_data_lower)
                #print("YES lots1")
            elif "lot : lot-00" in text_data_lower:
                lots = re.split('lot : lot-00',text_data_lower)
                #print("YES lots2")
                
            cpv_at_source_lot = ''
            for i in lots[1:]:
                lot_details_data = lot_details()
                lot_details_data.lot_number = lot_number
 
                try:
                    lot_details_data.lot_actual_number = 'LOT-00'+i.split('\n')[0].strip()
                except:
                    pass
 
                lot_details_data.lot_title = i.split('titre :')[1].split('\n')[0].strip()
                lot_details_data.lot_title_english = GoogleTranslator(source='auto', target='en').translate(lot_details_data.lot_title)
 
                try:
                    lot_details_data.lot_description = i.split('description :')[1].split('\n')[0].strip()
                    lot_details_data.lot_description_english = GoogleTranslator(source='auto', target='en').translate(lot_details_data.lot_description)
                except:
                    pass
 
                try:
                    lot_details_data.lot_contract_type_actual = i.split('nature du marché :')[1].split('\n')[0].strip()
                    if "fournitures" in lot_details_data.lot_contract_type_actual :
                        lot_details_data.contract_type = 'Supply'
                    elif 'marché de travaux' in lot_details_data.lot_contract_type_actual :
                        lot_details_data.contract_type = 'Works' 
                    elif "services" in lot_details_data.lot_contract_type_actual :
                        lot_details_data.contract_type = 'Service' 
                except:
                    pass
 
                try:
                    cpv_regex = re.compile(r'\b\d{8}\b')
                    cpv = cpv_regex.findall(i)
                    lot_cpv_at_source = ''
                    class_title_at_source = ''
                    for code in cpv:
 
                        try:
                            class_title_at_source  += i.split(code)[1].split('\n')[0].strip()
                            class_title_at_source  += ','
                        except:
                            pass
 
                        lot_cpv_at_source += code
                        lot_cpv_at_source += ','
  
                        lot_cpvs_data = lot_cpvs()
 
                        lot_cpvs_data.lot_cpv_code = code
 
                        lot_cpvs_data.lot_cpvs_cleanup()
                        lot_details_data.lot_cpvs.append(lot_cpvs_data)
                    lot_details_data.lot_cpv_at_source = lot_cpv_at_source.rstrip(',')
                    lot_details_data.lot_class_codes_at_source = lot_cpv_at_source.rstrip(',')
                    notice_data.class_title_at_source = class_title_at_source.rstrip(',')
                except:
                    pass
 
                try:
                    lot_quantity = i.split('quantité :')[1].split('\n')[0].strip()
                    lot_details_data.lot_quantity_uom = re.findall('\w+',lot_quantity)[-1]
                    lot_quantity = lot_quantity.replace(',','.')
                    lot_details_data.lot_quantity = float(lot_quantity)
                except Exception as e:
                    logging.info("Exception in lot_quantity: {}".format(type(e).__name__))
                    pass
 
                try:
                    lot_details_data.contract_duration = i.split('durée : ')[1].split('\n')[0].strip()
                except:
                    pass
 
                try:
                    contract_start_date = i.split('date de début :')[1].split('\n')[0].strip()
                    contract_start_date = re.findall('\d+/\d+/\d{4}',contract_start_date)[0]
                    lot_details_data.contract_start_date = datetime.strptime(contract_start_date,'%d/%m/%Y').strftime('%Y/%m/%d %H:%M:%S')
                except Exception as e:
                    logging.info("Exception in contract_start_date: {}".format(type(e).__name__))
                    pass
 
                try:
                    contract_end_date  = i.split('date de fin de durée : ')[1].split('\n')[0].strip()
                    contract_end_date  = re.findall('\d+/\d+/\d{4}',contract_end_date )[0]
                    lot_details_data.contract_end_date  = datetime.strptime(contract_end_date ,'%d/%m/%Y').strftime('%Y/%m/%d %H:%M:%S')
                except Exception as e:
                    logging.info("Exception in contract_end_date : {}".format(type(e).__name__))
                    pass
 
                try:
                    lot_netbudget_lc  = i.split('valeur estimée hors tva :')[1].split('\n')[0].strip()
                    lot_netbudget_lc  = re.sub('[^\d\.\,]','',lot_netbudget_lc )
                    lot_netbudget_lc  = lot_netbudget_lc .replace(',','')
                    lot_details_data.lot_netbudget_lc  = float(lot_netbudget_lc)
                except Exception as e:
                    logging.info("Exception in netbudgetlc1: {}".format(type(e).__name__)) 
                    pass  
 
                try: 
                    lot_netbudget_lc  = i.split("valeur maximale de l'accord-cadre :")[1].split('\n')[0].strip()
                    lot_netbudget_lc4  = re.sub("[^\d\.\,]","",lot_netbudget_lc)
                    lot_netbudget_lc1  = lot_netbudget_lc4.replace(',','')
                    lot_details_data.lot_netbudget_lc2  = float(lot_netbudget_lc1)
                except Exception as e:
                    logging.info("Exception in netbudgetlc2: {}".format(type(e).__name__)) 
                    pass  
 
                try:
                    criteria = i.split("critères d'attribution")[1].split('critère :')
                    for criterias in criteria[1:]:
                        lot_criteria_data = lot_criteria()
 
                        lot_criteria_data.lot_criteria_title = criterias.split('type :')[1].split('\n')[0].strip()
 
                        if 'prix' in lot_criteria_data.lot_criteria_title:
                            lot_criteria_data.lot_is_price_related = True
 
                        list_data = ["pondération (points, valeur exacte) :","pondération (pourcentage, valeur exacte) :"]         
                        for data_split in list_data:
                            lot_criteria_data.lot_criteria_weight = int(criterias.split(data_split)[1].split('\n')[0].strip())
 
                        if lot_criteria_data.lot_criteria_title != '':
                            lot_criteria_data.lot_criteria_cleanup()
                            lot_details_data.lot_criteria.append(lot_criteria_data)
                except:
                    pass
  
                lot_details_data.lot_details_cleanup()
                notice_data.lot_details.append(lot_details_data)
                lot_number += 1
        except Exception as e:
            logging.info("Exception in lot_details: {}".format(type(e).__name__)) 
            pass      
        try: 
            cpv_at_source = ''
            text_data_remove = text_data.lower().replace('(','').replace(')','')
            for each_cpv in text_data_remove.split('cpv')[1:]:
                cpv_code1 = each_cpv
                if re.search("\d{8}", cpv_code1):
                    regex = re.findall(r'\b\d{8}\b',cpv_code1)
                    for each_cpvs in regex:
                        cpvs_data = cpvs()
                        cpvs_data.cpv_code = each_cpvs
                        cpv_at_source += each_cpvs
                        cpv_at_source += ','
                        cpvs_data.cpvs_cleanup()
                        notice_data.cpvs.append(cpvs_data)
            notice_data.cpv_at_source = cpv_at_source.rstrip(',')
            notice_data.class_codes_at_source = notice_data.cpv_at_source
        except Exception as e:
            logging.info("Exception in cpvs: {}".format(type(e).__name__)) 
            pass

    #***********************************************************************************************************************
 
        try:              
            customer_details_data = customer_details()
            customer_details_data.org_country = 'FR'
            customer_details_data.org_language = 'FR'
            customer_details_data.org_name = soup.select_one('#print_area_company ').get_text()
 
            try:
                customer_details_data.org_address = text_data.split('Nom et adresses :')[1].split('TÃ©l')[0].strip()
            except Exception as e:
                logging.info("Exception in org_address1: {}".format(type(e).__name__))
                pass
            try:
                org_address = soup.find('a', class_='ml-1').get_text().strip()
                customer_details_data.org_address = re.sub(r'\s+', ' ', org_address)
            except Exception as e:
                logging.info("Exception in org_address2: {}".format(type(e).__name__))
                pass
            try:  
                postal_code = re.search('code postal(.)+\d{5}',text_data.lower())
                code_postal = postal_code.group()
                customer_details_data.postal_code = re.findall('\d{5}',code_postal)[0]
            except Exception as e:
                logging.info("Exception in postal_code: {}".format(type(e).__name__))
                pass
 
            try:  
                customer_nuts = fn.get_after(text_data,'NUTS',25)
                data = re.findall('[A-Z0-9]{4,5}',customer_nuts)[0]
                lst = []
                code = lst.extend(data)
                if lst[-1].isalpha():
                    code = lst[0:-1]
                    customer_details_data.customer_nuts  = "".join(code)
                else:
                    customer_details_data.customer_nuts  = data
 
            except Exception as e:
                logging.info("Exception in customer_nuts: {}".format(type(e).__name__))
                pass
 
            try:
                customer_main_activity_word = ['Activité du pouvoir adjudicateur:','ActivitÃ© principale']
                for i in customer_main_activity_word:
                    if i in customer_main_activity_word:
                        try:
                            customer_details_data.customer_main_activity = text_data.split(i)[1].split('\n')[0].strip()
                        except:
                            pass
            except Exception as e:
                logging.info("Exception in customer_main_activity: {}".format(type(e).__name__))
                pass
 
            try:
                org_email_text =  text_data.lower()
                if "mail" in org_email_text:
                    org_email = fn.get_after(org_email_text,'mail',60)
                    customer_details_data.org_email =fn.get_email(org_email)
                elif 'e-mail' in org_email_text:
                    org_email = fn.get_after(org_email_text,'e-mail',60)
                    customer_details_data.org_email =fn.get_email(org_email)
                elif 'email' in org_email_text:
                    org_email = fn.get_after(org_email_text,'email',60)
                    customer_details_data.org_email =fn.get_email(org_email)
                elif 'courriel' in org_email_text:
                    org_email = fn.get_after(org_email_text,'courriel',60)
                    customer_details_data.org_email =fn.get_email(org_email)
                elif 'mèl' in org_email_text:
                    org_email = fn.get_after(org_email_text,'mèl',60)
                    customer_details_data.org_email =fn.get_email(org_email)
                else:
                    pass
            except Exception as e:
                logging.info("Exception in org_email: {}".format(type(e).__name__))
                pass
 
            try:
                contact_person = fn.get_after(text_data_lower,'nom du contact',60)
                if 'adresse mail du contact' in contact_person:
                    try:
                        customer_details_data.contact_person = contact_person.split(':')[1].split('adresse mail du contact')[0].strip()
                    except:
                        contact_person = text_data_lower.split('nom du contact')[1].split('adresse mail du contact')[0].strip()
                        customer_details_data.contact_person = contact_person.split(':')[1].strip()
                else:
                    contact_person = text_data_lower.split('nom du contact')[1].split('\n')[0].strip() 
                    customer_details_data.contact_person = contact_person.split(':')[1].strip()
            except Exception as e:
                logging.info("Exception in contact_person: {}".format(type(e).__name__))
                pass
 
            try:
                org_phone_words = ['téléphone','tél','tã©l']
                for i in org_phone_words:
                    if i in text_data_lower:
                        org_phone = fn.get_after(text_data_lower,i,30)
                        try:
                            customer_details_data.org_phone = re.findall('.\d+ \d{9}',org_phone)[0]
                        except:
                            try:
                                customer_details_data.org_phone = re.findall('\d{10}',org_phone)[0]
                            except:
                                try:
                                    org_phone_num = re.findall('\d[0-9]',org_phone)
                                    customer_details_data.org_phone = re.findall('\d{10}',''.join(org_phone_num))[0]
                                except:
                                    pass
            except Exception as e:
                logging.info("Exception in org_phone: {}".format(type(e).__name__))
                pass
 
            try:
                type_of_authority_code_words = ['type de pouvoir adjudicateur : ',"forme juridique de l'acheteur:","Forme juridique de l'acheteur:"]
                for i in type_of_authority_code_words:
                    if i in type_of_authority_code_words:
                        try:
                            customer_details_data.type_of_authority_code = text_data_lower.split(i)[1].split('\n')[0].strip()
                        except:
                            pass
            except Exception as e:
                logging.info("Exception in type_of_authority_code: {}".format(type(e).__name__))
                pass
 
            try:
                org_city = fn.get_after(text_data_lower,"ville :",40)
                if 'code postal' in org_city:
                    customer_details_data.org_city = org_city.split('code postal')[0].strip()
            except Exception as e:
                logging.info("Exception in org_city: {}".format(type(e).__name__))
                pass
 
            try:
                try:
                    customer_details_data.org_website = text_data_lower.split('web :')[1].split('/')[-1].strip()
                except:
                    customer_details_data.org_website = text_data_lower.split('adresse principale :')[1].split('\n')[0].strip()
            except Exception as e:
                logging.info("Exception in org_website: {}".format(type(e).__name__))
                pass
 
            try:
                customer_details_data.org_fax = text_data_lower.split('fax :')[1].split('\n')[0].strip()
            except Exception as e:
                logging.info("Exception in org_fax: {}".format(type(e).__name__))
                pass
 
            customer_details_data.customer_details_cleanup()
            notice_data.customer_details.append(customer_details_data)
        except Exception as e:
            logging.info("Exception in customer_details: {}".format(type(e).__name__)) 
            pass
 
        try:
            lst = ["d'envoi du présent avis","d'envoi de l'avis","d'envoi du présent avis à la publication"]
            for i in lst:
                if i in text_data:
                    dispatch_date = text_data.split(i)[1].strip()
                    dispatch_date_en = GoogleTranslator(source='auto', target='en').translate(dispatch_date)
                    try:
                        dispatch_date = re.findall('\d+/\d+/\d{4}',dispatch_date)[0]
                        notice_data.dispatch_date = datetime.strptime(dispatch_date,'%d/%m/%Y').strftime('%Y/%m/%d')
                    except:
                        try:
                            dispatch_date_en = re.findall('\w+ \d+, \d{4}',dispatch_date_en)[0]
                            notice_data.dispatch_date = datetime.strptime(dispatch_date_en,'%B %d, %Y').strftime('%Y/%m/%d')
                        except: 
                            try:
                                dispatch_date_en = re.findall('\d+ \w+ \d{4}',dispatch_date_en)[0]
                                notice_data.dispatch_date = datetime.strptime(dispatch_date_en,'%d %m %Y').strftime('%Y/%m/%d')
                            except:
                                try:
                                    dispatch_date = re.findall('\d{4}-\d+-\d+',dispatch_date)[0]
                                    notice_data.dispatch_date = datetime.strptime(dispatch_date,'%Y-%m-%d').strftime('%Y/%m/%d')
                                except:
                                    pass
 
        except Exception as e:
            logging.info("Exception in dispatch_date: {}".format(type(e).__name__))
            pass
 
        try:
            contract_duration_word =  ["Durée","Durée du marché"]
            for i in contract_duration_word:
                if i in contract_duration_word:
                    try:
                        contract_duration = text_data.split(i)[1].split('\n')[0].strip()
                        if contract_duration!='':
                            if re.search("\d+", contract_duration):
                                notice_data.contract_duration = contract_duration
                        else:
                            notice_data.contract_duration = text_data.split(i)[2].split('\n')[0].strip()
                    except:
                        pass
 
            if notice_data.contract_duration is None or notice_data.contract_duration =='':
                try:
                    contract_duration = text_data.split("Durée du marché")[1].split('\n')[1].split('\n')[0].strip()
                except:
                    contract_duration = text_data.split("Durée du marché")[1].split('\n')[1].split('\n')[0].strip()
                if re.search("\d+", contract_duration):
                    notice_data.contract_duration = contract_duration
 
        except Exception as e:
            logging.info("Exception in contract_duration: {}".format(type(e).__name__))
            pass
 
        try:
            notice_data.local_description = text_data.split('Description')[1].split('Identifiant de la procédure:')[0].strip()
            notice_data.notice_summary_english = GoogleTranslator(source='auto', target='en').translate(notice_data.local_description)
        except Exception as e:
            logging.info("Exception in local_description: {}".format(type(e).__name__))
            pass   
 
                
    else:
        print('Failed to retrieve the webpage')
 
#***********************************************************************************************************************
    #use identifier for keep each record unice 
    notice_data.identifier = str(notice_data.script_name) + str(notice_data.notice_no) +  str(notice_data.notice_type) +  str(notice_data.notice_url) 
    logging.info(notice_data.identifier)
    notice_data.tender_cleanup() 
    output_json_file.writeNoticeToJSONFile(jsons.dump(notice_data)) # each record dump into json file
    notice_count += 1
    t_notice_count  += 1
    logging.info('----------------------------------')
# ----------------------------------------- Main Body
 
# -------- make directory for store all download xml file.
#Taken path that directory of where you want store xml files and concat folder name with today date.
 
tmp_dwn_dir = application_properties.TMP_DIR + "/fr_marcheson_down_file"+ "_" + datetime.now().strftime('%Y%m%d')
if os.path.exists(tmp_dwn_dir):
    pass
else:
    os.makedirs(tmp_dwn_dir)
#--------- taken date threshold for data we want data from yesterday. threshold means yesterday date.
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    #-------- Load main url with the helpf of beautifull soup library and use request.get() function.
    #response.status_code use for url behavear html.parser use for all data grab with content without any error.
    # all rows grab by select function have taken commen select in select function and roted with for loop and get all url on web page.
    urls = ['https://www.marchesonline.com/rss-appels-d-offres'] 
    for url in urls:
        logging.info('----------------------------------')
        logging.info(url)
        response = requests.get(url)
        if response.status_code == 200:   
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.select('body > div.homepage > div > div > div:nth-child(6) > div > ul > li > ul > li > p > a')
            for records in rows:
                xml_url = records.get('href')
                sub_url = "https://www.marchesonline.com"+str(xml_url)
                save_path = sub_url.split('rss/')[1].strip() # taken only names from urls for create xml file.
                response = requests.get(sub_url)
                if response.status_code == 200:
                    with open(tmp_dwn_dir+'/'+save_path, 'wb') as file: # wight all xml files in that fr_marcheson_down_file.
                        file.write(response.content)
                    logging.info("File downloaded successfully.") # if file wight then print this statement.
                else:
                    logging.info(f"Failed to download file.") # if file is not wight then print this statement.
        else:
            logging.info(f"Failed to response.")
            
#**************************************************************************************************************
        # this code use for grab totel list of files from xml_file
    time.sleep(10) # use time function for wait.
    path = tmp_dwn_dir
    dir_list = os.listdir(path)  # taken list of all xml files from that fr_marcheson_down_file folder.
    csv_file_path = tmp_dwn_dir+'/fr_marcheson_spn_data.csv' # make csv file path.
    fr_marcheson_spn_filter = []
    column_names = ["title", "pubDate", "link"]
    for files in dir_list: # all xml iterate by for loop.
        with open(os.path.join(path, files), 'r') as file: # open one by one xml file.
           ##  grab each notice from xml file into item tag 
            data = file.read() # read one by one xml file.
            root = ET.fromstring(data)
            for xmldata in root.findall('.//item'):  # grab only data in item tag from each xml file.
                pub_Date = xmldata.find('pubDate').text
                pub_Date = re.findall('\d+ \w+ \d{4} \d+:\d+:\d+',pub_Date)[0]
                pub_Date = datetime.strptime(pub_Date,'%d %b %Y %H:%M:%S').strftime('%Y/%m/%d %H:%M:%S')
                if pub_Date >= threshold:
                    title = xmldata.find('title').text
                    link = xmldata.find('link').text
                    fr_marcheson_spn_filter.append((title, pub_Date, link))
        # remove xml file after extract require data 
        os.remove(tmp_dwn_dir+f"/{files}") 
    logging.info(f"Finished processing, {len(fr_marcheson_spn_filter)} record available greater than {threshold}") # count all record from fr_marcheson_spn_filter list.
    with open(csv_file_path, mode='w', newline='') as file: # dump above list in csv file 
        writer = csv.writer(file)
        writer.writerow(column_names) 
        writer.writerows(fr_marcheson_spn_filter)
    with open(csv_file_path, 'r', encoding="windows-1252") as f: # open csv file and read mode.
        lines = f.readlines() 
        dict_reader = csv.DictReader(lines)
        csv_data = list(dict_reader)
        for tender_html_element in csv_data:
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break
            if notice_count == 50:
                output_json_file.copyFinalJSONToServer(output_json_folder) # made back hend function to dump all records in json file.
                output_json_file = gec_common.OutputJSON.OutputJSON(SCRIPT_NAME)
                notice_count = 0
 
    os.remove(csv_file_path)  #remove csv file
    logging.info("Finished processing. Scraped {} notices".format(t_notice_count))
except Exception as e:
    raise e
    logging.info("Exception:"+str(e))
finally:
    output_json_file.copyFinalJSONToServer(output_json_folder) # finally whole data dump in json file use function.