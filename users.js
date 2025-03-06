if (!localStorage.getItem('users')) {
    localStorage.setItem('users', JSON.stringify({ 'e': 'e', 'Nurmuhammed': '4' }));
}

const signup_error_msg = document.getElementById('error_msg')

function get_users() {
    return JSON.parse(localStorage.getItem('users'));
}

function add_user(name, pw1, pw2) {
    let users = get_users();

    if (name && pw1 && pw2) {
        if (users[name]) {
            signup_error_msg.textContent = "Username already exists";
            return false;
        }

        if (pw1 !== pw2) {
            signup_error_msg.textContent = "Passwords do not coincide";
            return false;
        }
    }
    else {
        signup_error_msg.textContent = "Input fields can not be empty";
        return false;
    }

    users[name] = pw1;
    localStorage.setItem('users', JSON.stringify(users));
    return true;
}

function check_user_login(name,pw){
    let users = get_users();
    if (name && pw){
        for (let key in users){
            if (key === name && users[key] === pw) return true;
        }
        return false;
    }
    return false;
}