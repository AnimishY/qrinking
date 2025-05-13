import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

def create_database_schema():
    """Create the database schema for the QR code application"""
    
    # Load environment variables
    load_dotenv()
    
    # Database connection parameters from environment variables
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT')),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_NAME'),
        'use_pure': True,  # Use pure Python implementation
    }
    
    # Add SSL if required
    if os.getenv('DB_SSL', 'False').lower() == 'true':
        db_config['ssl_disabled'] = False
    
    try:
        # Establish connection to MySQL server
        connection = mysql.connector.connect(**db_config)
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL
            )
            """)
            
            # Create qr_codes table - removed image_url as we'll generate images on-the-fly
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS qr_codes (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                link TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
            """)
            
            connection.commit()
            print("Database schema created successfully")
            
    except Error as e:
        print(f"Error: {e}")
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == "__main__":
    create_database_schema()
