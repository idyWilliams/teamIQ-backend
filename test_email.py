import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_brevo_connection():
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = 'noreply@isentrytechnologies.com'
        msg['To'] = 'widorenyin0@gmail.com'  # Your email
        msg['Subject'] = 'Test Email from Brevo'
        
        body = 'This is a test email'
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        server = smtplib.SMTP('smtp-relay.brevo.com', 587)
        server.starttls()
        server.login('989629002@smtp-brevo.com', '2Wkt6xObV5PUwFnC')
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Actually call the function
test_brevo_connection()
