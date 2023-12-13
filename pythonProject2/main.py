import os
import re
import socket
import threading
import email
import time
import pyodbc
import base64
from email import encoders, policy
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser


def get_email_content(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload()
    else:
        return msg.get_payload()

def parse_email(email_bytes):
    msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
    attachments = []
    if msg.is_multipart():
        for part in msg.iter_parts():
            content_disposition = part['Content-Disposition']
            if content_disposition and 'attachment' in content_disposition:
                content = part.get_payload(decode=False)  # Do not decode the content
                content=content.rstrip()
                filename = part.get_filename()
                attachments.append((filename, content))

    return attachments

def ReceiveInfor(email_str):
    msg = email.message_from_string(email_str)

    body_content = get_email_content(msg)

    sender = msg['From']

    if sender.find('<')!=-1:
        sender = re.search(r'<([^<>]+)>', sender).group(1)

    receiver_list = msg['To'].split(',')

    cc_list = msg['Cc'].split(',') if msg['Cc'] else []


    subject = msg['Subject']

    attachments = parse_email(email_str.encode())

    return sender, receiver_list, cc_list, subject, body_content, attachments
class User :
    def __init__(self,username):
        self.connection_string='DRIVER={ODBC Driver 17 for SQL Server};SERVER=ISHIGAMI;DATABASE=Socket;UID=ishigami;PWD=123'
        self.username=username
        self.userid=None
        self.pw=None
        self.mailserver=None
        self.smtp=None
        self.pop3=None
        self.autoload=None

        conn =pyodbc.connect(self.connection_string)
        cursor=conn.cursor()
        cursor.execute('SELECT * FROM General_Config WHERE UserName=?',(self.username))
        row=cursor.fetchone()

        if row:
            self.userid,self.username,self.pw,self.mailserver,self.smtp,self.pop3,self.autoload=row
        else:
            self.pw=input('Enter password : ')
            self.mailserver=input('Enter Mail Server : ')
            self.smtp=int(input('Enter SMTP port : '))
            self.pop3=int(input('Enter POP3 port : '))
            self.autoload=int(input('Enter time for autoload mail : '))
            cursor.execute('INSERT INTO General_Config (UserName,Password,MailServer,SMTP,POP3,Autoload) VALUES(?,?,?,?,?,?)',(self.username,self.pw,self.mailserver,self.smtp,self.pop3,self.autoload))
            conn.commit()
            cursor.execute('SELECT * FROM General_Config WHERE UserName=?', (self.username))
            row = cursor.fetchone()
            self.userid,self.username,self.pw,self.mailserver,self.smtp,self.pop3,self.autoload=row
        conn.close()
    def SendEmail(self,mailreceiver,subject,content,CClist = None ,BCClist = None ,filenames=[]):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.mailserver, self.smtp))
        rps = client.recv(1024).decode()

        client.send(f'EHLO {self.smtp}\r\n'.encode())
        rps = client.recv(1024).decode()

        client.send(f'MAIL FROM: {self.username}\r\n'.encode())
        rps = client.recv(1024).decode()

        if mailreceiver:
            for e in mailreceiver:
                client.send(f'RCPT TO: {e}\r\n'.encode())
                rps = client.recv(1024).decode()

        if CClist:
            for e in CClist:
                client.send(f'RCPT TO: {e}\r\n'.encode())
                rps = client.recv(1024).decode()
        if BCClist:
            for e in BCClist:
                client.send(f'RCPT TO: {e}\r\n'.encode())
                rps = client.recv(1024).decode()

        client.send('DATA\r\n'.encode())
        rps = client.recv(1024).decode()

        message = MIMEMultipart()
        message["From"] = f'{self.username}'
        message["To"] = ', '.join(mailreceiver)
        message["Subject"] = f'{subject}'
        message["Cc"] = ', '.join(CClist)

        body = f"""{content}"""

        message.attach(MIMEText(body, 'plain'))

        for filename in filenames:
            filesize= os.path.getsize(filename)
            if (filesize>3 * 1024 * 1024) :
                print(f'FILE {filename} vượt quá kích thước (3mb) cho phép không thể gửi !!!!')
                continue

            with open(filename, 'rb') as attachment:
                # Tạo một phần MIMEBase
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

                # Mã hóa phần nội dung của email
                encoders.encode_base64(part)

                # Thêm header cho phần đính kèm
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename= "{os.path.basename(filename)}"',
                )
                # Đính kèm phần vào tin nhắn
                message.attach(part)

        text = message.as_string()
        msg = text
        client.send(msg.encode())

        client.send('\r\n.\r\n'.encode())
        rps = client.recv(1024).decode()

        client.send('QUIT\r\n'.encode())
        client.close()

    def AutoDownMail(self):
        autoload_time =self.autoload
        conn = pyodbc.connect(self.connection_string)
        cursor = conn.cursor()
        # Tao folder cho User neu chua ton tai
        folder_names = ['Inbox', 'Important', 'Work', 'Project', 'Spam']
        cursor.execute("SELECT FolderName FROM Folders WHERE UserId = ?", (self.userid))
        existing_folders = [row.FolderName for row in cursor.fetchall()]
        for folder_name in folder_names:
            if folder_name not in existing_folders:
                cursor.execute("INSERT INTO Folders (FolderName, UserId) VALUES (?, ?)", (folder_name, self.userid))
        conn.commit()

        # Xu ly FilterRule table
        cursor.execute("SELECT COUNT(*) FROM FilterRule WHERE UserId = ?", (self.userid))
        (count,) = cursor.fetchone()
        if count == 0:
            from_field = "ahihi@testing.com,ahuu@testing.com"
            subject_field = "urgent,ASAP"
            content_field = "report,meeting"
            content_subject_field = 'virus,hack,crack'

            from_moveto_folder = 'Project'
            subject_moveto_folder = 'Important'
            content_moveto_folder = 'Work'
            content_subject_moveto_folder = 'Spam'
            other_moveto_folder = 'Inbox'

            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, from_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute(
                "INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                ('From', from_field, folderid, self.userid, from_moveto_folder))
            conn.commit()

            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, subject_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute(
                "INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                ('Subject', subject_field, folderid, self.userid, subject_moveto_folder))
            conn.commit()

            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, content_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute(
                "INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                ('Content', content_field, folderid, self.userid, content_moveto_folder))
            conn.commit()

            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, content_subject_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute(
                "INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                ('ContentAndSubject', content_subject_field, folderid, self.userid, content_subject_moveto_folder))
            conn.commit()

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'From' AND UserId = ?", (self.userid))
        row = cursor.fetchone()
        from_field = row[1]
        from_field = from_field.split(',')
        from_moveto_foldeid = row[2]
        # print(from_field)
        # print(from_moveto_foldeid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'Subject' AND UserId = ?", (self.userid))
        row = cursor.fetchone()
        subject_field = row.FIELD
        subject_field = subject_field.split(',')
        subject_moveto_folderid = row.FolderId
        # print(subject_field)
        # print(subject_moveto_folderid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'Content' AND UserId = ?", (self.userid))
        row = cursor.fetchone()
        content_field = row.FIELD
        content_field = content_field.split(',')
        content_moveto_folderid = row.FolderId
        # print(content_field)
        # print(content_moveto_folderid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'ContentAndSubject' AND UserId = ?", (self.userid))
        row = cursor.fetchone()
        contentandsubject_field = row[1]
        contentandsubject_fieldld = contentandsubject_field.split(',')
        contentandsubject_moveto_foldeid = row[2]
        # print(contentandsubject_fieldld)
        # print(contentandsubject_moveto_foldeid)

        cursor.execute("SELECT FolderId FROM Folders WHERE FolderName = ? AND UserId=?", ('Inbox', self.userid))
        InboxId = cursor.fetchone()
        InboxId = InboxId[0]
        # print(InboxId)
        while True:
            time.sleep(autoload_time)
            # print('Đang kiểm tra email mới...')
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((socket.gethostname(), self.pop3))
            rps = client.recv(1024).decode()
            # print(rps)

            client.send(f'USER {self.username}\r\n'.encode())
            rps = client.recv(1024).decode()
            # print(rps)

            password = base64.b64encode(f'{self.pw}'.encode())
            client.send(b'PASS ' + password + b'\r\n')
            rps = client.recv(1024).decode()
            # print(rps)

            client.send(b'STAT\r\n')
            rps = client.recv(1024).decode()
            # print(rps)
            _, num, _ = rps.split()
            num = int(num)

            client.settimeout(2.5)
            for i in range(1, num + 1):
                client.send(f'RETR {i}\r\n'.encode())
                chunks = []
                try:
                    while True:
                        chunk = client.recv(1024)
                        if len(chunk) == 0:
                            break
                        chunks.append(chunk)
                except socket.timeout:
                    print("")
                rps = b''.join(chunks).decode()
                rps = rps.split('\n', 1)[1]
                sender, receiver, cc_list, subject, email_body, attachments = ReceiveInfor(rps)
                cc_list = ', '.join(cc_list)
                receiver = ', '.join(receiver)
                folderid = 0
                if sender in from_field:
                    folderid = from_moveto_foldeid

                if folderid == 0:
                    subject_each_char = subject.split()
                    for x in subject_each_char:
                        if x in subject_field:
                            folderid = subject_moveto_folderid

                if folderid == 0:
                    body_each_char = email_body.split()
                    for x in body_each_char:
                        if x in content_field:
                            folderid = content_moveto_folderid

                if folderid == 0:
                    subject_each_char = subject.split()
                    for x in subject_each_char:
                        if x in contentandsubject_field:
                            folderid = contentandsubject_moveto_foldeid
                            break
                    body_each_char = email_body.split()
                    for x in body_each_char:
                        if x in contentandsubject_field:
                            folderid = contentandsubject_moveto_foldeid

                if folderid == 0:
                    folderid = InboxId

                attachment_string = ' '
                for atm in attachments:
                    attachment_string += '('
                    attachment_string += atm[1]
                    attachment_string += ','
                    attachment_string += atm[0]
                    attachment_string += '),'

                cursor.execute(
                    'INSERT INTO Emails (Sender,Receiver,Subject,Content,Attachment,FolderId,Status,CC) VALUES(?,?,?,?,?,?,?,?)',
                    (sender, receiver, subject, email_body, attachment_string, folderid, 0, cc_list))
                conn.commit()
            #
            for i in range(1, num + 1):
                client.send(f'DELE {i}\r\n'.encode())
                rps = client.recv(1024).decode()

            client.send(b'QUIT\r\n')
            client.close()


    def ReceiveMail(self):
        conn =pyodbc.connect(self.connection_string)
        cursor=conn.cursor()

        #Tao folder cho User neu chua ton tai
        folder_names = ['Inbox', 'Important', 'Work', 'Project', 'Spam']
        cursor.execute("SELECT FolderName FROM Folders WHERE UserId = ?", (self.userid))
        existing_folders = [row.FolderName for row in cursor.fetchall()]
        for folder_name in folder_names:
            if folder_name not in existing_folders:
                cursor.execute("INSERT INTO Folders (FolderName, UserId) VALUES (?, ?)", (folder_name, self.userid))
        conn.commit()


        #Xu ly FilterRule table
        cursor.execute("SELECT COUNT(*) FROM FilterRule WHERE UserId = ?", (self.userid))
        (count,) = cursor.fetchone()
        if count == 0:
            from_field = "ahihi@testing.com,ahuu@testing.com"
            subject_field = "urgent,ASAP"
            content_field = "report,meeting"
            content_subject_field ='virus,hack,crack'

            from_moveto_folder='Project'
            subject_moveto_folder='Important'
            content_moveto_folder='Work'
            content_subject_moveto_folder='Spam'
            other_moveto_folder='Inbox'

            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid,from_moveto_folder))
            row=cursor.fetchone()
            folderid =row.FolderId
            cursor.execute("INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                       ('From', from_field, folderid, self.userid,from_moveto_folder))
            conn.commit()


            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, subject_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute("INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                           ('Subject', subject_field, folderid, self.userid,subject_moveto_folder))
            conn.commit()


            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, content_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute("INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                           ('Content', content_field, folderid, self.userid,content_moveto_folder))
            conn.commit()


            cursor.execute('SELECT * FROM Folders WHERE UserId = ? AND FolderName = ?',
                           (self.userid, content_subject_moveto_folder))
            row = cursor.fetchone()
            folderid = row.FolderId
            cursor.execute("INSERT INTO FilterRule (Type, FIELD, FolderId, UserId,FolderName) VALUES (?, ?, ?, ?,?)",
                           ('ContentAndSubject', content_subject_field, folderid, self.userid, content_subject_moveto_folder))
            conn.commit()


        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'From' AND UserId = ?", (self.userid))
        row=cursor.fetchone()
        from_field = row[1]
        from_field=from_field.split(',')
        from_moveto_foldeid=row[2]
        # print(from_field)
        # print(from_moveto_foldeid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'Subject' AND UserId = ?", (self.userid))
        row=cursor.fetchone()
        subject_field = row.FIELD
        subject_field=subject_field.split(',')
        subject_moveto_folderid=row.FolderId
        # print(subject_field)
        # print(subject_moveto_folderid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'Content' AND UserId = ?", (self.userid))
        row=cursor.fetchone()
        content_field = row.FIELD
        content_field=content_field.split(',')
        content_moveto_folderid=row.FolderId
        # print(content_field)
        # print(content_moveto_folderid)

        cursor.execute("SELECT * FROM FilterRule WHERE Type = 'ContentAndSubject' AND UserId = ?", (self.userid))
        row = cursor.fetchone()
        contentandsubject_field = row[1]
        contentandsubject_fieldld = contentandsubject_field.split(',')
        contentandsubject_moveto_foldeid = row[2]
        # print(contentandsubject_fieldld)
        # print(contentandsubject_moveto_foldeid)

        cursor.execute("SELECT FolderId FROM Folders WHERE FolderName = ? AND UserId=?",('Inbox',self.userid))
        InboxId=cursor.fetchone()
        InboxId=InboxId[0]
        # print(InboxId)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((socket.gethostname(), self.pop3))
        rps = client.recv(1024).decode()
        # print(rps)

        client.send(f'USER {self.username}\r\n'.encode())
        rps = client.recv(1024).decode()
        # print(rps)

        password = base64.b64encode(f'{self.pw}'.encode())
        client.send(b'PASS ' + password + b'\r\n')
        rps = client.recv(1024).decode()
        # print(rps)

        client.send(b'STAT\r\n')
        rps = client.recv(1024).decode()
        # print(rps)
        _, num, _ = rps.split()
        num = int(num)

        client.settimeout(2.5)
        for i in range(1, num + 1):
            client.send(f'RETR {i}\r\n'.encode())
            chunks = []
            try:
                while True:
                    chunk = client.recv(1024)
                    if len(chunk) == 0:
                        break
                    chunks.append(chunk)
            except socket.timeout:
                print("")
            rps = b''.join(chunks).decode()
            rps = rps.split('\n', 1)[1]

            sender,receiver,cc_list,subject,email_body,attachments=ReceiveInfor(rps)
            cc_list = ', '.join(cc_list)
            receiver= ', '.join(receiver)

            folderid=0
            if sender in from_field:
                folderid=from_moveto_foldeid

            if folderid==0:
                subject_each_char=subject.split()
                for x in subject_each_char:
                    if x in subject_field:
                        folderid=subject_moveto_folderid

            if folderid==0:
                body_each_char=email_body.split()
                for x in body_each_char:
                    if x in content_field:
                        folderid=content_moveto_folderid

            if folderid==0:
                subject_each_char = subject.split()
                for x in subject_each_char:
                    if x in contentandsubject_fieldld:
                        folderid=contentandsubject_moveto_foldeid
                        break
                body_each_char = email_body.split()
                for x in body_each_char:
                    if x in contentandsubject_fieldld:
                        folderid=contentandsubject_moveto_foldeid


            if folderid==0:
                folderid=InboxId

            attachment_string = ' '
            for atm in attachments:
                attachment_string += '('
                attachment_string += atm[1]
                attachment_string += ','
                attachment_string += atm[0]
                attachment_string += '),'



            cursor.execute(
                'INSERT INTO Emails (Sender,Receiver,Subject,Content,Attachment,FolderId,Status,CC) VALUES(?,?,?,?,?,?,?,?)',
                (sender, receiver, subject, email_body, attachment_string, folderid, 0, cc_list))
            conn.commit()


        for i in range(1, num + 1):
            client.send(f'DELE {i}\r\n'.encode())
            rps = client.recv(1024).decode()

        client.send(b'QUIT\r\n')
        client.close()

        print("""
        Đây là danh sách các folder trong mailbox của bạn:
        1. Inbox
        2. Important
        3. Work
        4. Project
        5. Spam
        """)
        wantId = int(input('ENTER MAILBOX YOU WANT TO OPEN : '))
        dictionary = {1:'Inbox',2:'Important',3:'Work',4:'Project',5:'Spam'}

        cursor.execute('SELECT FolderId FROM Folders WHERE FolderName = ? AND UserId=?',(dictionary[wantId],self.userid))
        folderwantedid = cursor.fetchone()[0]
        # print(folderwantedid)

        cursor.execute('SELECT * FROM Emails WHERE FolderId=?',(folderwantedid))
        emails = cursor.fetchall()
        # print(emails)
        if emails:
            print(f"Đây là danh sách email trong {dictionary[wantId]} folder:")
            print('STT : Trạng Thái : Người gửi : Chủ đề !')
            for index, email in enumerate(emails, start=1):
                status = "(chưa đọc)" if email[7] == False else "(đã đọc)"
                sender = email[1].strip()  # Loại bỏ các ký tự xuống dòng và khoảng trắng thừa
                subject = email[3].strip()
                print(f"{index}  {status} || {sender} || {subject}")

            choose = int(input('Chọn số thứ tự thư muốn mở : '))
            email_to_open = emails[choose - 1]
            email_id = email_to_open[0]
            cursor.execute('UPDATE Emails SET Status = 1 WHERE EmailId = ?', (email_id,))
            conn.commit()
            print(f"Đang mở email số {choose}...")
            print(f"Người gửi: {email_to_open[1]}")
            print(f'Người nhận : {email_to_open[2]}')
            print(f'CC: {email_to_open[8]}')
            print(f"Chủ đề: {email_to_open[3]}")
            print(f"Nội dung: {email_to_open[4]}")

            attachments = email_to_open[5]
            # print(attachments)
            if attachments == " ":
                print("Không có tệp đính kèm.")
            else:
                print('Đây là tệp tin trong mail .')
                attachments = attachments.split(',')
                attachments = [a for a in attachments if a]

                attachments = ','.join(attachments)
                attachments = attachments.strip('()').split('),(')

                for i, attachment in enumerate(attachments, start=1):
                    content_base64, filename = attachment.split(',')
                    print(f"{i}. {filename}")

                choose = int(input('Có muốn tải file về máy không ? 1 hoặc 0 '))
                if choose == 1:
                    path = input('Nhập path folder muốn tải về  : ')
                    choose = int(input('Muốn tải file số mấy ? Nhập 0 để tải tất cả.  : '))
                    if choose == 0:
                        # Tải xuống tất cả các tệp
                        for i, attachment in enumerate(attachments, start=1):
                            content_base64, filename = attachment.split(',')
                            file_data = base64.b64decode(content_base64)
                            file_path = os.path.join(path, filename)
                            with open(file_path, 'wb') as f:
                                f.write(file_data)
                            print(f"Tệp {i} đã được tải xuống thành công tại {file_path}")
                    else:
                        # Tải xuống tệp được chọn
                        attachment_to_download = attachments[choose - 1]
                        content_base64, filename = attachment_to_download.split(',')
                        file_data = base64.b64decode(content_base64)
                        file_path = os.path.join(path, filename)
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                        print(f"Tệp đã được tải xuống thành công tại {file_path}")
            choose = int(input('Có muốn DI CHUYỂN mail này vào folder khác không ? 1:CÓ - 0:KHÔNG '))
            if choose==1:
                print('''
                    1. Inbox
                    2. Important
                    3. Work
                    4. Project
                    5. Spam
                    ''')
                choose = int(input('Muốn di chuyển email này vào thư mục nào ? : '))

                cursor.execute('SELECT FolderId FROM Folders WHERE FolderName = ? AND UserId=?',
                               (dictionary[choose], self.userid))
                folderwantedid = cursor.fetchone()[0]
                cursor.execute('UPDATE Emails SET FolderId = ? WHERE EmailId = ?', (folderwantedid,email_id,))
                conn.commit()
                print(f'Đã di chuyển mail đến thư mục {dictionary[choose]} thành công .')
        else:
            print("Không có email trong folder này.")

def main():
    username=input('Enter mail : ')
    user=User(username)

    thread = threading.Thread(target=user.AutoDownMail, daemon=True)
    thread.start()

    choose =int(input("""
    Vui lòng chọn Menu:
    1. Để gửi email
    2. Để xem danh sách các email đã nhận
    3. Thoát
"""))
    if choose==1:
        print('Đây là thông tin soạn email:')

        #TO
        mailreceiver=[]
        n=int(input('Nhập vào số lượng mail người muốn gửi || nTO : '))
        for i in range(n):
            mr = input(f"Nhập vào mail của người muốn gửi thứ {i + 1} || TO :  ")
            mailreceiver.append(mr)

        #CC
        CClist=[]
        sizecclist=int(input('Nhập vào số lượng mail người muốn gửi Carbon Copy || nCC : '))
        for i in range(sizecclist):
            cc = input(f"Nhập vào mail của người muốn gửi Carbon Copy thứ {i + 1} || CC :  ")
            CClist.append(cc)

        #BCC
        BCClist=[]
        sizeBcclist=int(input('Nhập vào số lượng mail người muốn gửi Blind Carbon Copy || nBCC : '))
        for i in range(sizeBcclist):
            bcc= input(f"Nhập vào mail của người muốn gửi Blind Carbon Copy thứ {i + 1} || BCC :  ")
            BCClist.append(bcc)

        #Subject
        subject=input('Nhập chủ đề của mail || Subject : ')

        #Content
        content = ""
        while True:
            line = input("Nhập content của bạn (hoặc 'END' để kết thúc): ")
            if line == "END":
                break
            content += line + "\n"
        content=content.rstrip()
        #file
        filenames = []
        num_files = int(input("Nhập số lượng tệp đính kèm: "))
        for i in range(num_files):
            file_path = input(f"Nhập đường dẫn của tệp đính kèm thứ {i + 1}: ")
            filenames.append(file_path)


        user.SendEmail(mailreceiver,subject,content,CClist,BCClist,filenames)
    elif choose==2:
        user.ReceiveMail()
    else:
        print('Kết thúc nhanh đến vậy sao !')


if __name__=="__main__":
    main()