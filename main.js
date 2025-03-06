document.addEventListener("DOMContentLoaded", init);

// DOM Elements
const usersList = document.getElementById("users");
const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const addContactBtn = document.getElementById("add-contact-btn");
const logoutBtn = document.getElementById("logout-btn");
const currentContactName = document.getElementById("current-contact-name");

// Global state variables
let currentUser = null;
let currentContact = null;
let contacts = [];

// Initialize the application
async function init() {
  try {
    // Check if user is logged in
    const response = await fetch('/api/me');
    const data = await response.json();
    
    if (!data.success) {
      // Redirect to login page if not logged in
      window.location.href = '/login';
      return;
    }
    
    // Set the current user
    currentUser = data.user;
    
    // Load contacts
    await loadContacts();
    
    // Setup event listeners
    setupEventListeners();
  } catch (error) {
    console.error('Error initializing app:', error);
    window.location.href = '/login';
  }
}

// Load user's contacts
async function loadContacts() {
  try {
    const response = await fetch('/api/contacts');
    const data = await response.json();
    
    if (data.success) {
      contacts = data.contacts;
      renderContacts();
    } else {
      console.error('Error loading contacts:', data.message);
    }
  } catch (error) {
    console.error('Error loading contacts:', error);
  }
}

// Render contacts list
function renderContacts() {
  if (contacts.length === 0) {
    usersList.innerHTML = '<li class="no-contacts">No contacts yet. Click + to add.</li>';
    return;
  }
  
  const contactListItems = contacts.map(contact => {
    const isActive = currentContact && currentContact.id === contact.id;
    return `<li class="${isActive ? 'active' : ''}" data-id="${contact.id}" data-username="${contact.username}">
      ${contact.username}
    </li>`;
  }).join("");
  
  usersList.innerHTML = contactListItems;
  
  // Add click event listeners to contact items
  document.querySelectorAll('#users li').forEach(item => {
    item.addEventListener('click', () => handleContactSelection(item));
  });
}

// Handle contact selection
async function handleContactSelection(contactElement) {
  // Get contact info from the clicked element
  const contactId = parseInt(contactElement.getAttribute('data-id'));
  const contactUsername = contactElement.getAttribute('data-username');
  
  // Update current contact
  currentContact = { id: contactId, username: contactUsername };
  
  // Update UI
  document.querySelectorAll('#users li').forEach(li => li.classList.remove('active'));
  contactElement.classList.add('active');
  currentContactName.textContent = contactUsername;
  
  // Enable input and send button
  messageInput.disabled = false;
  sendButton.disabled = false;
  
  // Load messages for this contact
  await loadMessages(contactId);
}

// Load messages for a specific contact
async function loadMessages(contactId) {
  try {
    messagesDiv.innerHTML = '<div class="loading-messages">Loading messages...</div>';
    
    const response = await fetch(`/api/messages/${contactId}`);
    const data = await response.json();
    
    if (data.success) {
      renderMessages(data.messages);
    } else {
      messagesDiv.innerHTML = '<div class="error-message">Failed to load messages</div>';
      console.error('Error loading messages:', data.message);
    }
  } catch (error) {
    messagesDiv.innerHTML = '<div class="error-message">Failed to load messages</div>';
    console.error('Error loading messages:', error);
  }
}

// Render messages in the chat box
function renderMessages(messages) {
  if (messages.length === 0) {
    messagesDiv.innerHTML = '<div class="no-messages">No messages yet. Start the conversation!</div>';
    return;
  }
  
  messagesDiv.innerHTML = messages.map(msg => {
    const isSentByMe = msg.sender_id === currentUser.id;
    const messageClass = isSentByMe ? 'sent' : 'received';
    return `<p class="${messageClass}">
      ${msg.message_text}
    </p>`;
  }).join("");
  
  // Scroll to the bottom of messages
  scrollMessagesToBottom();
}

// Send a message
async function sendMessage() {
  const messageText = messageInput.value.trim();
  
  if (!messageText || !currentContact) return;
  
  try {
    const response = await fetch('/api/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        receiver_id: currentContact.id,
        message: messageText
      }),
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Clear input field
      messageInput.value = "";
      
      // Reload messages
      await loadMessages(currentContact.id);
    } else {
      console.error('Error sending message:', data.message);
    }
  } catch (error) {
    console.error('Error sending message:', error);
  }
}

// Add a new contact
async function addContact() {
  const contactUsername = prompt("Enter the username to add as a contact:");
  
  if (!contactUsername) return;
  
  try {
    const response = await fetch('/api/contacts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username: contactUsername }),
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert(`${contactUsername} added as a contact!`);
      await loadContacts();
    } else {
      alert(data.message || 'Failed to add contact');
    }
  } catch (error) {
    console.error('Error adding contact:', error);
    alert('Failed to add contact. Please try again.');
  }
}

// Logout function
async function logout() {
  try {
    await fetch('/logout', {
      method: 'POST',
    });
    window.location.href = '/login';
  } catch (error) {
    console.error('Error logging out:', error);
  }
}

// Scroll to the bottom of messages
function scrollMessagesToBottom() {
  setTimeout(() => {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }, 0);
}

// Setup all event listeners
function setupEventListeners() {
  // Send button click
  sendButton.addEventListener("click", sendMessage);
  
  // Enter key press in message input
  messageInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      sendMessage();
    }
  });
  
  // Add contact button
  addContactBtn.addEventListener('click', addContact);
  
  // Logout button
  logoutBtn.addEventListener('click', logout);
}