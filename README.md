# Parser for tenders
 A program to parse, process and categorize data from procurement websites.
 
 Data is gathered from Tenders Electronic Daily, ECEPP (European Bank for Reconstruction and Development) and South African Tenders (as their robots.txt files allow parsing).
 
 Classification is carried out by logistic regression model to determine whether the subject of tender is relevant to nuclear industry (trained with self-made dataset, 500 objects gathered with parsers and labaled manually).
 
 A Jupiter notebook with logreg model training and BERT finetuning is included.
