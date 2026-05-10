from contextlib import contextmanager

from fintracker_base.databaseDAO.sqlConnector import get_connection, db
import hashlib
import os
from datetime import datetime, timedelta

# Rate limiting dictionary (in production, use Redis)
login_attempts = {}

def register(name, email, password):
    with db() as (_, cursor):
        query = "INSERT INTO users(name, email, password) VALUES (%s,%s,%s)"

        namecheck = nameChecker(name)
        emailcheck = isEmail(cursor, email)
        passwordcheck = checkpassword(password)

        # NOW CHECK THE FIRST ELEMENT OF THE TUPLE
        if not emailcheck[0]:
            return emailcheck
        if not passwordcheck[0]:
            return passwordcheck
        if not namecheck[0]:
            return namecheck
        else:
            hashedpw = hashpassword(password)
            cursor.execute(query, (name, email, hashedpw,))

            return True, "User registered successfully."


def isEmail(cursor, email):
    query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    if cursor.fetchone() is not None:
        print("This email is already registered. Please use a new email or continue with the current one.")
        return False, "Email already registered"
    else:
        return True, "Email available"


def hashpassword(password):
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt + ":" + hashed


def checkpassword(password):
    special = "!#€%&/()=?^*_:;©@£$∞§|[]≈±´~™''æ…‚§¶°"
    lower = "abcdefghijklmnopqrstuvwxyz"
    upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    num = "1234567890"

    if len(password) < 8:
        print("The password is too short, the password length should be larger than 8.")
        return False, "Password too short"

    if not any(c in special for c in password):
        print("The password does not contain any special symbols e.g. '!#€...'. ")
        return False, "Missing special character"
    if not any(c in lower for c in password):
        print("The password does not contain any small letters e.g. 'abc...'.")
        return False, "Missing lowercase letter"
    if not any(c in upper for c in password):
        print("The password does not contain any capital letters e.g. 'ABC....'. ")
        return False, "Missing uppercase letter"
    if not any(c in num for c in password):
        print("The password does not contain any numbers e.g. '123....'. ")
        return False, "Missing number"
    return True, "Password valid"


def nameChecker(name):
    newname = name.lower().strip()

    if len(newname) < 5:
        print("The name is too short.")
        return False, "Name too short"

    special = "!#€%&/()=?^*_:;©@£$∞§|[]≈±´~™''æ…‚§¶°"
    num = "1234567890"

    if any(c in special for c in newname):
        print("No special characters are allowed.")
        return False, "No special characters allowed"
    if any(c in num for c in newname):
        print("No numbers are allowed in Name.")
        return False, "No numbers allowed"
    return True, "Name valid"


def check_rate_limit(email):
    """Simple rate limiting for login attempts"""
    current_time = datetime.now()

    if email in login_attempts:
        attempts, last_attempt = login_attempts[email]

        if current_time - last_attempt > timedelta(minutes=15):
            login_attempts[email] = (1, current_time)
            return True

        if attempts >= 5:
            print(f"Too many login attempts for {email}. Try again in 15 minutes.")
            return False

        login_attempts[email] = (attempts + 1, current_time)
        return True
    else:
        login_attempts[email] = (1, current_time)
        return True


def logIn(email, password):
    if "@" not in email:
        print("This is not an email.")
        return False, None

    # Check rate limit BEFORE attempting login
    if not check_rate_limit(email):
        return False, None

    with db() as (conn, cursor):

        salt = passwordSalt(cursor, email)
        if not salt:
            print("The email or password is incorrect!")
            return False, None
        hashedPw = hashAgain(salt, password)

        query = "SELECT password, user_id FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        row = cursor.fetchone()
        if not row:
            print("Invalid email or password")
            return False, None

        stored_pw, user_id = row
        _, realHashpw = stored_pw.split(":")

        if hashedPw == realHashpw:
            print("Login Successful")
            # Reset rate limit on successful login
            if email in login_attempts:
                del login_attempts[email]
            return True, user_id
        else:
            print("The email or password is incorrect")
            return False, None


def passwordSalt(cursor, email):
    query = "SELECT password FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    if not result:
        return None
    salt, _ = result[0].split(":")
    return salt


def hashAgain(salt, password):
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed


def update_userinfo(email=None, name=None, new_email=None):

   with db() as (conn, cursor):
        query = "SELECT user_id FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        row = cursor.fetchone()
        if not row:
            print("The user does not exist")
            return False

        update = []
        value = []

        if name:
            namecheck = nameChecker(name)
            if not namecheck[0]:
                print("invalid name")
                return False
            update.append("name = %s")
            value.append(name)

        if new_email:
            emailcheck = isEmail(cursor, new_email)
            if not emailcheck[0]:
                print("invalid email")
                return False
            update.append("email = %s")
            value.append(new_email)

        value.append(email)
        query = f"UPDATE users SET {', '.join(update)} WHERE email = %s"
        cursor.execute(query, tuple(value))
        print("User information updated successfully.")
        return True


def update_password(email, old_password, password, re_password):

    with db() as (conn, cursor):
        query = "SELECT password FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        row = cursor.fetchone()
        if not row:
            print("The user does not exist!")
            return False

        storedPw = row[0]
        old_salt, realhashPw = storedPw.split(":")
        oldPassword_hash = hashAgain(old_salt, old_password)

        if oldPassword_hash != realhashPw:
            print("The password is incorrect!")
            return False
        else:
            newPasswordCheck = checkpassword(password)
            if not newPasswordCheck[0]:
                return False
            if password != re_password:
                print("The password input does not match the given password")
                return False
            else:
                query = "UPDATE users SET password = %s WHERE email = %s"
                newPassword_hash = hashpassword(password)
                cursor.execute(query, (newPassword_hash, email,))
                print("The password has been successfully changed!")
                return True
