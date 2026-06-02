import json
import os
from pathlib import Path
from typing import Optional, List
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
USERS_FILE = DATA_DIR / 'users.json'
CONTACTS_FILE = DATA_DIR / 'contacts.json'
ACTIVITY_LOG = DATA_DIR / 'activity.log'
SAMPLE_IMPORT_CSV = DATA_DIR / 'sample_import.csv'

class UserNode:
    def __init__(self, username: str, password: str, role: str, next_node: 'UserNode' = None):
        self.username = username
        self.password = password
        self.role = role
        self.next = next_node

    def to_dict(self):
        return {'username': self.username, 'password': self.password, 'role': self.role}

class UserList:
    def __init__(self):
        self.head: Optional[UserNode] = None
        self.load_from_file()

    def load_from_file(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not USERS_FILE.exists():
            self.head = None
            return
        with USERS_FILE.open('r', encoding='utf-8') as handle:
            users = json.load(handle)
        self.head = None
        for item in reversed(users):
            node = UserNode(item['username'], item['password'], item['role'], self.head)
            self.head = node

    def save_to_file(self):
        users = []
        current = self.head
        while current:
            users.append(current.to_dict())
            current = current.next
        with USERS_FILE.open('w', encoding='utf-8') as handle:
            json.dump(users, handle, indent=2)

    def find(self, username: str) -> Optional[UserNode]:
        current = self.head
        while current:
            if current.username == username:
                return current
            current = current.next
        return None

    def authenticate(self, username: str, password: str) -> Optional[UserNode]:
        node = self.find(username)
        if node and check_password_hash(node.password, password):
            return node
        return None

    def add(self, username: str, password: str, role: str) -> bool:
        if self.find(username) is not None or role not in ('admin', 'user'):
            return False
        # store hashed password
        hashed = generate_password_hash(password)
        new_node = UserNode(username, hashed, role, self.head)
        self.head = new_node
        self.save_to_file()
        log_activity(username, 'Created user account')
        return True

    def delete(self, username: str) -> bool:
        prev = None
        current = self.head
        while current:
            if current.username == username:
                if prev is None:
                    self.head = current.next
                else:
                    prev.next = current.next
                self.save_to_file()
                log_activity(username, 'Deleted user account')
                return True
            prev = current
            current = current.next
        return False

    def list_users(self) -> List[dict]:
        users = []
        current = self.head
        while current:
            users.append(current.to_dict())
            current = current.next
        return users

class ContactNode:
    def __init__(self, contact_id: int, first_name: str, last_name: str,
                 phone: str, email: str, address: str, notes: str,
                 next_node: 'ContactNode' = None):
        self.id = contact_id
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.email = email
        self.address = address
        self.notes = notes
        self.next = next_node

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'notes': self.notes,
        }

class ContactList:
    def __init__(self):
        self.head: Optional[ContactNode] = None
        self.next_id = 1
        self.load_from_file()

    def load_from_file(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not CONTACTS_FILE.exists():
            self.head = None
            self.next_id = 1
            return
        with CONTACTS_FILE.open('r', encoding='utf-8') as handle:
            contacts = json.load(handle)
        self.head = None
        max_id = 0
        for item in reversed(contacts):
            node = ContactNode(item['id'], item['first_name'], item['last_name'],
                               item['phone'], item['email'], item['address'], item['notes'], self.head)
            self.head = node
            max_id = max(max_id, item['id'])
        self.next_id = max_id + 1

    def save_to_file(self):
        contacts = []
        current = self.head
        while current:
            contacts.append(current.to_dict())
            current = current.next
        with CONTACTS_FILE.open('w', encoding='utf-8') as handle:
            json.dump(contacts, handle, indent=2)

    def exists_duplicate(self, candidate: ContactNode, exclude_id: Optional[int] = None) -> bool:
        current = self.head
        while current:
            if exclude_id is not None and current.id == exclude_id:
                current = current.next
                continue
            if current.id != candidate.id and (
                (candidate.phone and candidate.phone.lower() == current.phone.lower()) or
                (candidate.email and candidate.email.lower() == current.email.lower()) or
                (candidate.first_name.lower() == current.first_name.lower() and candidate.last_name.lower() == current.last_name.lower())
            ):
                return True
            current = current.next
        return False

    def add(self, data: dict, username: str) -> bool:
        node = ContactNode(self.next_id, data.get('first_name',''), data.get('last_name',''),
                           data.get('phone',''), data.get('email',''), data.get('address',''), data.get('notes',''), self.head)
        if self.exists_duplicate(node):
            return False
        self.head = node
        self.next_id += 1
        self.save_to_file()
        log_activity(username, f"Added contact {node.first_name} {node.last_name}")
        return True

    def find(self, contact_id: int) -> Optional[ContactNode]:
        current = self.head
        while current:
            if current.id == contact_id:
                return current
            current = current.next
        return None

    def update(self, contact_id: int, data: dict, username: str) -> bool:
        contact = self.find(contact_id)
        if contact is None:
            return False
        updated = ContactNode(contact.id,
                              data.get('first_name',''),
                              data.get('last_name',''),
                              data.get('phone',''),
                              data.get('email',''),
                              data.get('address',''),
                              data.get('notes',''))
        if self.exists_duplicate(updated, exclude_id=contact_id):
            return False
        contact.first_name = updated.first_name
        contact.last_name = updated.last_name
        contact.phone = updated.phone
        contact.email = updated.email
        contact.address = updated.address
        contact.notes = updated.notes
        self.save_to_file()
        log_activity(username, f"Updated contact {contact.id}")
        return True

    def delete(self, contact_id: int, username: str) -> bool:
        prev = None
        current = self.head
        while current:
            if current.id == contact_id:
                if prev is None:
                    self.head = current.next
                else:
                    prev.next = current.next
                self.save_to_file()
                log_activity(username, f"Deleted contact {contact_id}")
                return True
            prev = current
            current = current.next
        return False

    def list_all(self) -> List[ContactNode]:
        contacts = []
        current = self.head
        while current:
            contacts.append(current)
            current = current.next
        return contacts

    def search(self, query: str) -> List[ContactNode]:
        needle = query.lower()
        results = []
        current = self.head
        while current:
            if (needle in current.first_name.lower() or
                needle in current.last_name.lower() or
                needle in current.phone.lower() or
                needle in current.email.lower() or
                needle in current.address.lower() or
                needle in current.notes.lower()):
                results.append(current)
            current = current.next
        return results

    def sort(self, field: str) -> None:
        if field not in ('id', 'first_name', 'last_name'):
            field = 'id'
        self.head = self._merge_sort(self.head, field)

    def _merge_sort(self, head: Optional[ContactNode], field: str) -> Optional[ContactNode]:
        if head is None or head.next is None:
            return head
        left, right = self._split(head)
        left = self._merge_sort(left, field)
        right = self._merge_sort(right, field)
        return self._merge(left, right, field)

    def _split(self, head: ContactNode):
        slow = head
        fast = head.next
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
        middle = slow.next
        slow.next = None
        return head, middle

    def _merge(self, a: ContactNode, b: ContactNode, field: str) -> ContactNode:
        if a is None:
            return b
        if b is None:
            return a
        if self._compare(a, b, field) <= 0:
            a.next = self._merge(a.next, b, field)
            return a
        b.next = self._merge(a, b.next, field)
        return b

    def _compare(self, a: ContactNode, b: ContactNode, field: str) -> int:
        if field == 'id':
            return a.id - b.id
        left = getattr(a, field, '') or ''
        right = getattr(b, field, '') or ''
        return (left.lower() > right.lower()) - (left.lower() < right.lower())

    def export_csv(self) -> str:
        lines = ['id,first_name,last_name,phone,email,address,notes']
        for contact in self.list_all():
            values = [str(contact.id), contact.first_name, contact.last_name,
                      contact.phone, contact.email, contact.address, contact.notes]
            quoted = [f'"{v.replace("\"", "\"\"")}"' if ',' in v or '"' in v else v for v in values]
            lines.append(','.join(quoted))
        return '\n'.join(lines)

    def import_csv(self, csv_text: str) -> bool:
        rows = [line.strip() for line in csv_text.splitlines() if line.strip()]
        if len(rows) < 2:
            return False
        duplicates = False
        for line in rows[1:]:
            parts = [part.strip().strip('"') for part in line.split(',')]
            if len(parts) < 7:
                continue
            contact_id, first, last, phone, email, address, notes = parts[:7]
            if not first or not last:
                continue
            candidate = ContactNode(0, first, last, phone, email, address, notes)
            if self.exists_duplicate(candidate):
                duplicates = True
                continue
            self.add({'first_name': first, 'last_name': last, 'phone': phone,
                      'email': email, 'address': address, 'notes': notes}, 'importer')
        return duplicates

def ensure_default_data():
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        USER_STORE.add('admin', 'admin123', 'admin')
        USER_STORE.add('user', 'user123', 'user')
    if not CONTACTS_FILE.exists():
        CONTACT_STORE.add({'first_name': 'Alice', 'last_name': 'Martin', 'phone': '555-0101', 'email': 'alice.martin@example.com', 'address': '12 Maple Street', 'notes': 'Friend from college'}, 'system')
        CONTACT_STORE.add({'first_name': 'Brian', 'last_name': 'King', 'phone': '555-0202', 'email': 'brian.king@example.com', 'address': '24 Oak Avenue', 'notes': 'Work colleague'}, 'system')
    if not SAMPLE_IMPORT_CSV.exists():
        SAMPLE_IMPORT_CSV.write_text('id,first_name,last_name,phone,email,address,notes\n3,Clara,Johnson,555-0303,clara.johnson@example.com,18 Pine Road,New contact\n4,Derek,Lopez,555-0404,derek.lopez@example.com,9 Birch Lane,Conference lead\n', encoding='utf-8')

def log_activity(username: str, action: str):
    DATA_DIR.mkdir(exist_ok=True)
    with ACTIVITY_LOG.open('a', encoding='utf-8') as handle:
        handle.write(f"{username} | {action}\n")

USER_STORE = UserList()
CONTACT_STORE = ContactList()
