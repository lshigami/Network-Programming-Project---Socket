# Computer Networks Project - Mail Client using Socket

This is a Mail Client project that uses Socket to connect and exchange data with the Mail Server through the SMTP and POP3 protocols.

## Installation

### Prerequisites

- **Programming languages:**  Python
- **Supported environments:** Windows, Unix/Linux, macOS
- **Supporting libraries:** Socket,os,re,threading,MIME,email,...

### Installation Steps

1. Clone the repository:

    ```bash
    git clone [https://github.com/your-username/mail-client-socket.git](https://github.com/lshigami/Network-Programming-Project-Socket)
    ```

2. Run Fake mail server :
   

3. Configure and compile:
   
    - **Python:** Run the `.py` files with the Python interpreter.
      
## Main Features

1. **Send Email:**
   - Send to one or more recipient addresses (TO).
   - Send to one or more recipient addresses (CC).
   - Able to send attached files (file size <= 3MB).

2. **Download Email:**
   - Download email content from the Server's mailbox.
   - Save attached files to the client's local machine.

3. **Manage Email:**
   - Mark email status (read/unread).
   - Filter emails by sender address, subject, content.

4. **Automatic Email Download:**
   - Configure the time to automatically download emails from the Mailbox.

## Config File

- Use the config file to configure user information, Mail Server, automatic email download settings.
- Using table in SQL server file sql

## Report

- Contains information about the progress and details of the completed functions.

## Author

- Name: Nguyen Quang Thang

## License

This project is released under the MIT license. See [LICENSE](LICENSE) for details.
