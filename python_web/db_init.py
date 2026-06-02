from models import init_db, create_user, add_contact

if __name__ == '__main__':
    init_db()
    # create default accounts
    create_user('admin', 'admin123', 'admin')
    create_user('user', 'user123', 'user')
    # sample contacts
    add_contact({'first_name':'Alice','last_name':'Martin','phone':'555-0101','email':'alice.martin@example.com','address':'12 Maple Street','notes':'Friend from college'})
    add_contact({'first_name':'Brian','last_name':'King','phone':'555-0202','email':'brian.king@example.com','address':'24 Oak Avenue','notes':'Work colleague'})
    print('Database initialized.')
