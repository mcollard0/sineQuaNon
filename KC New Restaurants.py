#/bin/python3
"""

KC New Restaurants Monitor
Automated food business license tracking system

1. Download the KC New Restaurants data from: https://city.kcmo.org/kc/BusinessLicenseSearch/Default
2. Iterate / Filters for current year and food businesses
3. Insert MongoDB with new records
4. Send HTML email alert for new business

"""

import requests;
import re;
import csv;
import time;
import smtplib;
import os;
import logging;
import urllib.parse;
import argparse;
import random;
import tempfile;
from datetime import datetime;
from email.mime.text import MIMEText;
from email.mime.multipart import MIMEMultipart;
from typing import List, Dict, Tuple;

try:
    from pymongo import MongoClient;
    from pymongo.errors import ConnectionFailure;
    MONGODB_AVAILABLE = True;
except ImportError:
    print( "pymongo is not installed. Please install it using 'pip install pymongo' or 'apt install python3-pymongo'." );
    MONGODB_AVAILABLE = False;

#logger
logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s' );
handlers = [ logging.FileHandler( "kc_new_restaurants.log" ), logging.StreamHandler() ];
logging.getLogger().handlers = handlers;
logger = logging.getLogger( __name__ );

#Distilled list of business types that are food related -- changed to just be restaurants and grocery stores
FOOD_BUSINESS_TYPES = frozenset( [
    "Supermarkets and Other Grocery Retailers (except Convenience Retailers)",
    #"Drinking Places (Alcoholic Beverages)",
    #"Convenience Retailers",
    "Retail Bakeries",
    "All Other Specialty Food Retailers", 
    #"Beer Wine and Liquor Retailers",
    "Food (Health) Supplement Retailers",
    "Mobile Food Services",
    #"Caterers",
    "Full-Service Restaurants",
    "Limited-Service Restaurants",
    #"Food Service Contractors",
    "Snack and Nonalcoholic Beverage Bars",
    #"Breweries",
    #"Meat Retailers",
    #"Distilleries",
    "Confectionery and Nut Retailers",
    #"Wineries", 
    "Cafeterias Grill Buffets and Buffets",
    #"Ice Cream and Frozen Dessert Manufacturing"
] );

class KCRestaurant:
    def __init__( self, mongodb_uri: str = "", database_name: str = "kc_new_restaurants", collection_name: str = "restaurants" ):
        self.mongodb_uri = mongodb_uri;
        self.database_name = database_name;
        self.collection_name = collection_name;
        self.session = self.db = self.collection = self.client = None;    

        self.stats = { 'total_records': 0, 'food_businesses': 0, 'current_year_food': 0, 'new_businesses':0,
    'existing_businesses':0, 'download_time':0, 'processing_time':0 };

        self.new_businesses = [ ]; # new businesses found this run

    def _sanitize_uri_for_logging(self, uri: str) -> str:
        """Sanitize MongoDB URI for logging by removing credentials."""
        if not uri:
            return "[empty]";
        try:
            # Remove credentials from URI for logging
            if '@' in uri:
                # Format: mongodb://username:password@host:port/db
                parts = uri.split('@');
                if len(parts) >= 2:
                    protocol_part = parts[0].split('://')[0] + '://';
                    host_part = '@'.join(parts[1:]);
                    return f"{protocol_part}[credentials_removed]@{host_part}";
            return uri;
        except Exception:
            return "[uri_parse_error]";

    def _sanitize_email_for_logging(self, email: str) -> str:
        """Sanitize email address for logging by masking part of it."""
        if not email or '@' not in email:
            return "[invalid_email]";
        try:
            local, domain = email.split('@', 1);
            # Show first 2 chars of local part, mask the rest
            masked_local = local[:2] + '*' * max(0, len(local) - 2);
            return f"{masked_local}@{domain}";
        except Exception:
            return "[email_parse_error]";

    def setup_mongodb( self ) -> bool:
        try:
            self.client = MongoClient( self.mongodb_uri, serverSelectionTimeoutMS=5000 );
            self.client.admin.command( 'ping' );
            self.client.admin.command( 'ismaster' );
            # Sanitize URI for logging (remove credentials if present)
            sanitized_uri = self._sanitize_uri_for_logging(self.mongodb_uri)
            logger.info( f"Connected to MongoDB: {sanitized_uri}" );
            self.db = self.client[ self.database_name ];
            self.collection = self.db[ self.collection_name ];

            # Drop old indexes if they exist to prevent conflicts
            try:
                self.collection.drop_index( "business_name_1" );
                logger.info( "Dropped old business_name_1 index" );
            except:
                pass;  # Index may not exist
            
            # Create a compound unique index on business_name + address + business_type for franchise support
            self.collection.create_index( [ ( "business_name", 1 ), ( "address", 1 ), ( "business_type", 1 ) ], unique=True, background=True );
            self.collection.create_index( [ ( "insert_date", 1 ) ], background=True );

            logger.info( f"Setup database: {self.database_name}, collection: {self.collection_name}" );
            return True;

        except Exception as e:
            logging.error( f"Error setting up MongoDB: {e}" );
            return False;
    
    def flush_database( self ) -> bool:
        """Flush (truncate) the entire collection to start fresh."""
        if self.collection is None:
            logger.error( "MongoDB collection not initialized" );
            return False;
            
        try:
            # Get count before deletion for logging
            before_count = self.collection.count_documents( { } );
            
            # Delete all documents in the collection
            result = self.collection.delete_many( { } );
            
            logger.info( f"Flushed database collection '{self.collection_name}'" );
            logger.info( f"Deleted {result.deleted_count:,} documents (was {before_count:,} total)" );
            
            return True;
            
        except Exception as e:
            logger.error( f"Error flushing database collection: {e}" );
            return False;

    def download_kc_business_csv( self ) -> List[ List[ str ] ]:
        logger.info( "Downloading KC business license data..." );
        download_start = time.perf_counter();

        try:
            self.session = requests.Session();
            self.session.headers.update( {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            } );
            
            # Use the same approach as the working script
            url = "https://city.kcmo.org/kc/BusinessLicenseSearch/";
            
            logger.info( "  Getting initial search form..." );
            response = self.session.get( url );
            response.raise_for_status();
            
            # Extract form fields
            viewstate_match = re.search( r'__VIEWSTATE.*?value="([^"]*)"', response.text );
            generator_match = re.search( r'__VIEWSTATEGENERATOR.*?value="([^"]*)"', response.text );
            validation_match = re.search( r'__EVENTVALIDATION.*?value="([^"]*)"', response.text );
            
            if not all( [ viewstate_match, generator_match, validation_match ] ):
                logger.error( "Failed to extract necessary form fields from the initial page" );
                return [ ];
            
            logger.info( "  Submitting search form..." );
            form_data = {
                '__VIEWSTATE': viewstate_match.group( 1 ),
                '__VIEWSTATEGENERATOR': generator_match.group( 1 ),
                '__EVENTVALIDATION': validation_match.group( 1 ),
                'ctl00$MainContent$businessName': '',
                'ctl00$MainContent$dbaName': '',
                'ctl00$MainContent$address': '',
                'ctl00$MainContent$businessType': '',
                'ctl00$MainContent$expirationDate': '',
                'ctl00$MainContent$searchBtn': 'Begin Search'
            };
            
            response = self.session.post( url, data=form_data );
            response.raise_for_status();
            
            # Now we should have the search results page - look for export button
            logger.info( "  Looking for CSV export button..." );
            
            # Look for export button in various common patterns
            export_patterns = [
                r'<input[^>]*value="[^"]*Export[^"]*Data[^"]*"[^>]*name="([^"]+)"',
                r'<input[^>]*name="([^"]+)"[^>]*value="[^"]*Export[^"]*Data[^"]*"',
                r'<input[^>]*value="[^"]*Export[^"]*CSV[^"]*"[^>]*name="([^"]+)"',
                r'<input[^>]*name="([^"]+)"[^>]*value="[^"]*Export[^"]*CSV[^"]*"',
                r'href="([^"]*ExportToCSV[^"]*)"',
                r'<a[^>]*href="([^"]*export[^"]*csv[^"]*)"',
                r'onclick="[^"]*export[^"]*csv[^"]*"[^>]*name="([^"]+)"'
            ];
            
            export_button_name = None;
            export_url = None;
            
            for pattern in export_patterns:
                match = re.search( pattern, response.text, re.IGNORECASE );
                if match:
                    if 'href=' in pattern:
                        export_url = match.group( 1 );
                        logger.info( f"  Found export URL: {export_url}" );
                    else:
                        export_button_name = match.group( 1 );
                        logger.info( f"  Found export button: {export_button_name}" );
                    break;
            
            if export_url:
                # It's a direct link
                if not export_url.startswith( 'http' ):
                    export_url = urllib.parse.urljoin( url, export_url );
                logger.info( "  Downloading CSV via export URL..." );
                response = self.session.get( export_url );
                response.raise_for_status();
            elif export_button_name:
                # It's a form button - need to submit form again with export button
                logger.info( "  Submitting export form..." );
                
                # Extract updated form fields from results page
                viewstate_match = re.search( r'__VIEWSTATE.*?value="([^"]*)"', response.text );
                generator_match = re.search( r'__VIEWSTATEGENERATOR.*?value="([^"]*)"', response.text );
                validation_match = re.search( r'__EVENTVALIDATION.*?value="([^"]*)"', response.text );
                
                if not all( [ viewstate_match, generator_match, validation_match ] ):
                    logger.error( "Failed to extract form fields from results page" );
                    return [ ];
                
                export_form_data = {
                    '__VIEWSTATE': viewstate_match.group( 1 ),
                    '__VIEWSTATEGENERATOR': generator_match.group( 1 ),
                    '__EVENTVALIDATION': validation_match.group( 1 ),
                    export_button_name: 'Export to CSV'
                };
                
                response = self.session.post( url, data=export_form_data );
                response.raise_for_status();
            else:
                logger.error( "Could not find CSV export button or link" );
                logger.info( f"Response preview: {response.text[:1000]}" );
                
                # Save full response for debugging in a temporary file
                try:
                    with tempfile.NamedTemporaryFile( mode='w', suffix='_debug_response.html', delete=False, encoding='utf-8' ) as f:
                        f.write( response.text );
                        debug_file = f.name;
                    logger.info( f"Saved full response to {debug_file} for analysis" );
                except Exception as e:
                    logger.warning( f"Could not save debug file: {e}" );
                
                # Look for any forms or buttons that might be relevant
                forms = re.findall( r'<form[^>]*>.*?</form>', response.text, re.DOTALL | re.IGNORECASE );
                logger.info( f"Found {len(forms)} form(s) in response" );
                
                buttons = re.findall( r'<(?:input|button)[^>]*(?:type=["\']?(?:submit|button)["\']?|value=["\'][^"\'>]*(?:export|csv|download)[^"\'>]*["\'])[^>]*>', response.text, re.IGNORECASE );
                logger.info( f"Found potential buttons: {buttons}" );
                
                return [ ];

            #parsing
            csv_text = response.text;
            csv_lines = csv_text.splitlines();
            reader = csv.reader( csv_lines );
            rows = list( reader );
            
            self.stats[ 'download_time' ] = time.perf_counter() - download_start;

            # Debug: Print first few lines to see what we got
            logger.info( f"Response content type: {response.headers.get('content-type', 'unknown')}" );
            logger.info( f"Response status: {response.status_code}" );
            logger.info( f"First 500 chars of response: {csv_text[:500]}" );
            logger.info( f"Number of lines in response: {len(csv_lines)}" );
            if rows:
                logger.info( f"First row (header): {rows[0] if rows else 'None'}" );
                logger.info( f"Second row (sample): {rows[1] if len(rows) > 1 else 'None'}" );

            if rows and len( rows ) > 1:
                self.stats[ 'total_records' ] = len( rows ) - 1;
                logger.info( f"Downloaded {self.stats['total_records']} records from KC Business License data in {self.stats['download_time']:.2f} seconds" );
                return rows;

            logger.warning( "No data found in downloaded CSV" );
            return [ ];

        except Exception as e:
            logger.error( f"Error downloading KC Business License data: {e}" );
            return [ ];

    def is_food_business( self, business_type: str ) -> bool:
        return business_type.strip().strip( '"' ) in FOOD_BUSINESS_TYPES;

    def exists( self, business_name: str, address: str=None, business_type: str=None ) -> bool:
        """Check if a business already exists in the database based on name, address, and business type."""
        if self.collection is None: 
            return False;
        
        # Build query filter - all three fields must match for a duplicate
        query_filter = {
            "business_name": business_name,
            "address": address,
            "business_type": business_type
        };

        try: 
            logging.debug( f"Checking if exists: {business_name} at {address} ({business_type})" );
            existing_count = self.collection.count_documents( query_filter, limit=1 );
            return existing_count > 0;
        except Exception as e:
            logging.error( f"Error checking restaurant in DB: {e}" );
            return False;

    def process( self, csv_rows: List[ List[ str ] ] ) -> bool: 
        if not csv_rows or len( csv_rows ) < 2:
            logger.warning( "No data to process" );
            return False;

        processing_start = time.perf_counter();
        current_year = time.localtime().tm_year;
        header = csv_rows[ 0 ];
        expected_header = [ 'Business Name', 'DBA Name', 'Address', 'Business Type', 'Valid License For' ];
        
        if header != expected_header:
            logger.error( f"Unexpected CSV header. Expected: {expected_header}, Found: {header}" );
            return False;

        logger.info( f"Processing business license data..." );
        logger.info( f" Processing {len(csv_rows)-1:,} records..." );
        
        mongodb_not_initialized_warned = False;
        
        for row in csv_rows[ 1: ]:
            if len( row ) < 5:
                logger.warning( f"Skipping malformed row: {row}" );
                continue;

            business_name = row[ 0 ].strip().strip( '"' );
            dba_name = row[ 1 ].strip().strip( '"' );
            address = row[ 2 ].strip().strip( '"' );
            business_type = row[ 3 ].strip().strip( '"' );
            valid_license_for = row[ 4 ].strip().strip( '"' );  # This is the year

            if not self.is_food_business( business_type ): 
                continue;

            self.stats[ 'food_businesses' ] += 1;

            try:
                license_year = int( valid_license_for );
                if license_year != current_year: 
                    continue;
            except ( ValueError, TypeError ):
                logger.warning( f"Skipping row with invalid license year: {valid_license_for} for {business_name}" );
                continue;
            
            self.stats[ 'current_year_food' ] += 1;

            if self.exists( business_name, address, business_type ):
                self.stats[ 'existing_businesses' ] += 1;
                continue;
            
            # Create document for new business
            document = {
                "business_name": business_name,
                "dba_name": dba_name,
                "address": address,
                "business_type": business_type,
                "valid_license_for": valid_license_for,
                "insert_date": time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() ),
                "deleted": False
            };
            
            if self.collection is not None:
                try:
                    self.collection.insert_one( document.copy() );
                    logger.debug( f"Inserted new business: {business_name}, {address}, {business_type}" );
                except Exception as e:
                    logger.error( f"Error inserting new business into DB: {e}" );
            else:
                if not mongodb_not_initialized_warned:
                    logger.warning( "MongoDB collection not initialized - running in no-persistence mode" );
                    mongodb_not_initialized_warned = True;

            self.stats[ 'new_businesses' ] += 1;
            new_business = document.copy();
            new_business.pop( 'insert_date' );
            new_business.pop( 'deleted', None );
            self.new_businesses.append( new_business );

        self.stats[ 'processing_time' ] = time.perf_counter() - processing_start;
        logger.info( f"Processed {self.stats['total_records']} total records, found {self.stats['food_businesses']} food businesses in {self.stats['processing_time']:.2f} seconds" );

        return True;
    def generate_email_html( self ) -> str:
        if not self.new_businesses:
            return "<p>No new food businesses found this run.</p>";

        current_time = datetime.now().strftime( '%Y-%m-%d %H:%M:%S' );
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h2 {{ color: #2c5aa0; }}
                table {{ border-collapse: collapse; width: 99%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                a {{ color: #1a73e8; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h2>KC New Restaurants Businesses Alert</h2>
            
            <div class="summary">
                <strong>Summary for {current_time}:</strong>
                <ul>
                    <li>Total records processed: {self.stats['total_records']:,}</li>
                    <li>Food businesses found: {self.stats['food_businesses']:,}</li>
                    <li>Current year food businesses: {self.stats['current_year_food']:,}</li>
                    <li><strong>New businesses added: {len(self.new_businesses):,}</strong></li>
                    <li>Existing businesses (no change): {self.stats['existing_businesses']:,}</li>
                </ul>
            </div>
            
            <h3>New Food Businesses ({len(self.new_businesses)} found):</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Restaurant Name</th>
                        <th>Business Type</th>
                    </tr></thead>
                <tbody>
        """;

        for food in self.new_businesses:
            friendly_name = food.get( 'dba_name', '' ).strip() + ' (' + food.get( 'business_name', '' ).strip() + ')' if food.get( 'dba_name', '' ).strip() else food.get( 'business_name', '' ).strip();
            google_link = f"https://www.google.com/search?q="+ urllib.parse.quote_plus( friendly_name + " " + food.get('address', '') ) +"";
            html += f"""
                <tr>
                    <td><b><a href="{google_link}">{friendly_name}<br>{food.get('address', '')}</a></b></td>
                    
                    <td>{food.get('business_type', '')}</td>
                </tr>
            """;

        html += f"""
            </tbody>
                </table>
                <div class="footer">
                    <p>Report generated: {current_time}</p>
                    <p>Processing time: {self.stats['processing_time']:.2f}sec | Download time: {self.stats['download_time']:.2f}s</p>
                    <p>Click business names to search on Google</p>
                </div>
        </body>
        </html>
        """;

        return html;

    def send_email_alert( self, 
                        smtp_server: str = "smtp.gmail.com",
                        smtp_port: int = 587,
                        sender_email: str = "",
                        sender_password: str = "",
                        recipient_email: str = "",
                        subject: str = None ) -> bool:
        
        if not all( [ sender_email, sender_password, recipient_email ] ):
            logger.error( "Email credentials or recipient not provided." );
            return False;   

        try:
            html = self.generate_email_html();
            msg = MIMEMultipart( 'alternative' );
            msg[ 'From' ] = sender_email;
            msg[ 'To' ] = recipient_email;
            msg[ 'Subject' ] = subject if subject else f"KC New Restaurants Alert - {len( self.new_businesses )} New Businesses Found";   

            html_part = MIMEText( html, 'html' );
            msg.attach( html_part );
            logger.info( f"Connecting to SMTP server {smtp_server}:{smtp_port}" );

            with smtplib.SMTP( smtp_server, smtp_port ) as server:
                server.starttls();
                server.login( sender_email, sender_password );
                server.sendmail( sender_email, recipient_email, msg.as_string() );
                # Sanitize email for logging
                sanitized_email = self._sanitize_email_for_logging(recipient_email)
                logger.info( f"Email sent to {sanitized_email}" );
                return True;

        
        except Exception as e:
            logger.error( f"Error sending email: {e}" );
            return False;
        
    def run( self ) -> bool:
        try:
            logger.info( "Starting KC New Restaurants processing" );
            start_time = time.perf_counter();  

            csv_rows = self.download_kc_business_csv();
            if not csv_rows:
                logger.error( "No data downloaded, exiting" );
                return False;   
            if not self.process( csv_rows ):
                logger.error( "Error processing data, exiting" );
                return False;
            

            print( "\n" + "="*60 );
            print( "KC FOOD BUSINESS MONITOR RESULTS" );
            print( "="*60 );
            print( f"Statistics:" );
            print( f"   Total records processed: {self.stats['total_records']:,}" );
            print( f"   Food businesses found: {self.stats['food_businesses']:,}" );
            print( f"   New businesses added: {self.stats['new_businesses']:,}" );
            print( f"   Existing businesses: {self.stats['existing_businesses']:,}" );
            total_time = time.perf_counter() - start_time;
            print( f"   Total processing time: {total_time:.2f}s" );
            
            print( f"\nNew Food Businesses Found ({len(self.new_businesses)}):" );

            if not self.new_businesses:
                print( "   No new food businesses found this run." );
                return False;
            else:   
                for food in self.new_businesses:
                    friendly_name = food.get( 'dba_name', '' ).strip() + ' (' + food.get( 'business_name', '' ).strip() + ')' if food.get( 'dba_name', '' ).strip() else food.get( 'business_name', '' ).strip();
                    print( f" - {friendly_name} {food['address']} {food['business_type']} (License: {food['valid_license_for']})" );
                print( "\n" + "="*60 + "\n" );
                return True;
        except Exception as e:      
            logger.error( f"Error in run method: {e}" );
            return False;

def is_running_under_cron():
    """Detect if the script is being run by cron."""
    # Check for common cron indicators
    cron_indicators = [
        os.getenv( 'CRON' ) is not None,  
        os.getenv( 'TERM' ) is None,      
        os.getenv( 'HOME' ) == '/var/spool/cron',  
        not os.isatty( 0 ),               
        os.getppid() == 1               
    ];
    
    minimal_env = len( [ k for k in os.environ.keys() if not k.startswith( '_' ) ] ) < 10;
    
    return any( cron_indicators ) or minimal_env;

def apply_random_delay( skip_delay=False ):
    """Apply a random delay of 1-15 minutes if running under cron (unless skipped)."""
    if skip_delay:
        logger.info( "Skipping random delay due to --nodelay option" );
        return;
        
    if is_running_under_cron():
        delay_minutes = random.randint( 1, 15 );
        delay_seconds = delay_minutes * 60;
        logger.info( f"Detected cron execution - applying random delay of {delay_minutes} minutes ({delay_seconds} seconds)" );
        logger.info( f"   This helps distribute server load. Use --nodelay to skip this delay." );
        time.sleep( delay_seconds );
        logger.info( f"Delay completed, proceeding with execution" );
    else:
        logger.info( "Interactive execution detected - no delay applied" );

def main():
    parser = argparse.ArgumentParser(
        description='KC New Restaurants Monitor - Download and track Kansas City food business licenses'
    );
    parser.add_argument(
        '--ephemeral', '-e',
        action='store_true',
        help='Run in ephemeral mode without MongoDB (for testing/debugging)'
    );
    parser.add_argument(
        '--flush', '-f',
        action='store_true',
        help='Flush (truncate) the database collection before processing to start fresh'
    );
    parser.add_argument(
        '--nodelay',
        action='store_true',
        help='Skip the random delay even when running under cron (use with caution)'
    );
    
    args = parser.parse_args();
    
    apply_random_delay( skip_delay=args.nodelay );

    CONFIG = {
        'mongodb_uri': os.getenv( "MONGODB_URI", "" ),
        'database_name': "kansas_city",
        'collection_name': "food_businesses",
        'smtp_server': "smtp.gmail.com",
        'smtp_port': 587,
        'sender_email': os.getenv( "SENDER_EMAIL", "" ),  # Your Gmail address
        'sender_password': os.getenv( "SENDER_PASSWORD", "" ),  # Your Gmail App Password
        'recipient_email': os.getenv( "RECIPIENT_EMAIL", "" ),      # Where to send alerts
        'email_subject': f"KC Food Business Alert - {datetime.now().strftime('%Y-%m-%d')}"
    };

    runner = KCRestaurant( CONFIG[ 'mongodb_uri' ], CONFIG[ 'database_name' ], CONFIG[ 'collection_name' ] );
    
    #  ephemeral mode
    if args.ephemeral:
        print( "\nEPHEMERAL MODE: Running without MongoDB persistence (testing/debugging mode)" );
        print( "   - No database connection will be established" );
        print( "   - All businesses will be treated as 'new' for this run" );
        print( "   - No data will be persisted between runs\n" );

    elif MONGODB_AVAILABLE:
        if not runner.setup_mongodb():
            print( "\nMongoDB setup failed. Running in ephemeral mode." );
        else:

            if args.flush:
                print( "\nFLUSH MODE: Clearing all existing data from database..." );
                if runner.flush_database():
                    print( "Database flushed successfully. All records will appear as new.\n" );
                else:
                    print( "Failed to flush database. Exiting." );
                    return;
    else:
        print( "\nPyMongo not available. Running in ephemeral mode." );
    
    runner.run();

    if all( [ CONFIG[ 'sender_email' ], CONFIG[ 'sender_password' ], CONFIG[ 'recipient_email' ] ] ):
        print( f"\nSending email alert..." );
        success = runner.send_email_alert(
            smtp_server=CONFIG[ 'smtp_server' ],
            smtp_port=CONFIG[ 'smtp_port' ],
            sender_email=CONFIG[ 'sender_email' ],
            sender_password=CONFIG[ 'sender_password' ],
            recipient_email=CONFIG[ 'recipient_email' ],
            subject=CONFIG[ 'email_subject' ]
        );
        if success:
            print( "Email alert sent successfully" );
        else:
            print( "Email alert failed" );
    else:
        print( f"\nEmail not configured:" );
        print( "To enable email alerts, update the CONFIG section with:" );
        print( "* sender_email: Your Gmail address" );
        print( "* sender_password: Your Gmail App Password" );  
        print( "* recipient_email: Where to send alerts" );

if __name__ == "__main__":
    main();

