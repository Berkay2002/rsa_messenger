document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM fully loaded and parsed");

    const socket = io();

    const sidebar = document.getElementById("sidebar");
    const friendsList = document.getElementById("friends-list");
    const groupsList = document.getElementById("groups-list");
    const createGroupBtn = document.getElementById("create-group-btn");
    const newGroupNameInput = document.getElementById("new-group-name");
    const groupMembersInput = document.getElementById("group-members");
    const groupErrorMessage = document.getElementById("group-error-message");

    const chatContainer = document.getElementById("chat-container");
    const currentChatName = document.getElementById("current-chat-name");
    const chatMessages = document.getElementById("chat-messages");
    const messageInput = document.getElementById("message");
    const sendBtn = document.getElementById("send-btn");
    const errorMessage = document.getElementById("error-message");

    let username = "";
    let publicKey = "";
    let privateKey = "";
    let currentChat = null; // Can be a username or group name
    let isGroupChat = false;

    // Fetch Friends
    async function fetchFriends() {
        try {
            const response = await fetch(`/get_friends?username=${encodeURIComponent(username)}`);
            const data = await response.json();
            if (response.status === 200) {
                populateList(friendsList, data.friends, false);
            } else {
                console.error("Failed to fetch friends:", data.error);
            }
        } catch (error) {
            console.error("Error fetching friends:", error);
        }
    }

    // Fetch Groups
    async function fetchGroups() {
        try {
            const response = await fetch(`/get_groups?username=${encodeURIComponent(username)}`);
            const data = await response.json();
            if (response.status === 200) {
                populateList(groupsList, data.groups, true);
            } else {
                console.error("Failed to fetch groups:", data.error);
            }
        } catch (error) {
            console.error("Error fetching groups:", error);
        }
    }

    // Populate Friends or Groups List
    function populateList(listElement, items, isGroup) {
        listElement.innerHTML = "";
        items.forEach(item => {
            const li = document.createElement("li");
            li.textContent = item;
            li.classList.add("list-item");
            li.addEventListener("click", () => openChat(item, isGroup));
            listElement.appendChild(li);
        });
    }

    // Open Chat (Friend or Group)
    function openChat(chatName, group = false) {
        currentChat = chatName;
        isGroupChat = group;
        currentChatName.textContent = isGroupChat ? `Group: ${chatName}` : `Chat with: ${chatName}`;
        chatMessages.innerHTML = "";
        chatContainer.style.display = "flex";

        if (isGroupChat) {
            // Join the Socket.IO room for the group
            socket.emit("join_group", { group_name: chatName, username });
        }

        // Optionally, fetch chat history here
    }

    // Initialize Application after Login
    async function initializeApp() {
        await fetchFriends();
        await fetchGroups();
    }

    // Create Group
    async function createGroup() {
        const groupName = newGroupNameInput.value.trim();
        const members = groupMembersInput.value.split(',').map(m => m.trim()).filter(m => m !== "");

        if (!groupName || members.length === 0) {
            groupErrorMessage.textContent = "Group name and at least one member are required.";
            return;
        }

        // Add the creator to the members list if not already included
        if (!members.includes(username)) {
            members.push(username);
        }

        try {
            const response = await fetch('/create_group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_name: groupName,
                    creator: username,
                    members: members,
                }),
            });

            const data = await response.json();
            if (response.status === 201) {
                // Group created successfully
                fetchGroups();  // Refresh the groups list
                newGroupNameInput.value = "";
                groupMembersInput.value = "";
                groupErrorMessage.textContent = "";
                alert(`Group '${groupName}' created successfully.`);
            } else {
                groupErrorMessage.textContent = data.error || "Failed to create group.";
            }
        } catch (error) {
            console.error("Error creating group:", error);
            groupErrorMessage.textContent = "An error occurred while creating the group.";
        }
    }

    // Send Message
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!currentChat) {
            alert("No chat selected.");
            return;
        }
        if (!message) {
            alert("Message cannot be empty.");
            return;
        }

        if (isGroupChat) {
            // Encrypt message with each group member's public key if end-to-end encryption is desired
            // For simplicity, we'll assume group messages are broadcasted as encrypted by the sender

            // Emit group message
            socket.emit("new_message", { recipient: currentChat, message: encryptMessage(message, publicKey), is_group: true });
            appendMessage(`Me to ${currentChat}: ${message}`);
            messageInput.value = "";
        } else {
            // One-on-one message
            // Fetch recipient's public key
            try {
                const response = await fetch(`/get_public_key?username=${encodeURIComponent(currentChat)}`);
                const data = await response.json();
                if (response.status === 200 && data.public_key) {
                    console.log(`Fetched public key for ${currentChat}:`, data.public_key);
                    // Encrypt the message using recipient's public key
                    const encrypted = encryptMessage(message, data.public_key);
                    console.log("Encrypted Message:", encrypted);

                    // Emit the message with recipient info
                    socket.emit("new_message", { recipient: currentChat, message: encrypted, is_group: false });
                    appendMessage(`Me to ${currentChat}: ${message}`);
                    messageInput.value = "";
                } else {
                    showError(`Public key for ${currentChat} not found.`);
                    console.error(`Public key for ${currentChat} not found.`);
                }
            } catch (error) {
                console.error("Error fetching public key:", error);
                showError("Failed to fetch recipient's public key.");
            }
        }
    }

    // Append Message to Chat
    function appendMessage(message) {
        const li = document.createElement("li");
        li.textContent = message;
        chatMessages.appendChild(li);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Encrypt Message
    function encryptMessage(message, pubKey) {
        const encrypt = new JSEncrypt();
        encrypt.setPublicKey(pubKey);
        const encryptedMessage = encrypt.encrypt(message);
        console.log("Message encrypted with public key:", encryptedMessage);
        return encryptedMessage;
    }

    // Decrypt Message
    function decryptMessage(encryptedMessage) {
        const decrypt = new JSEncrypt();
        decrypt.setPrivateKey(privateKey);
        const decrypted = decrypt.decrypt(encryptedMessage);
        if (decrypted) {
            console.log("Message decrypted successfully:", decrypted);
            return decrypted;
        } else {
            console.error("Decryption failed for message:", encryptedMessage);
            return "Decryption failed.";
        }
    }

    // Encrypt Private Key
    function encryptPrivateKey(privateKey, password) {
        try {
            // Encrypt the private key using AES with the password
            const encrypted = CryptoJS.AES.encrypt(privateKey, password).toString();
            return encrypted;
        } catch (error) {
            console.error("Error encrypting private key:", error);
            return null;
        }
    }

    // Decrypt Private Key
    function decryptPrivateKey(encryptedPrivateKey, password) {
        try {
            // Decrypt the private key using AES with the password
            const bytes = CryptoJS.AES.decrypt(encryptedPrivateKey, password);
            const decrypted = bytes.toString(CryptoJS.enc.Utf8);
            console.log("Decrypted Private Key:", decrypted);
            return decrypted || null;
        } catch (e) {
            console.error("Private key decryption failed:", e);
            return null;
        }
    }

    // Show Error Message
    function showError(message) {
        console.error("Error:", message);
        errorMessage.textContent = message;
    }

    // Create Group Event Listener
    createGroupBtn.addEventListener("click", createGroup);

    // Handle User Login
    async function handleLogin() {
        console.log("JOIN button clicked");
        username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        if (!username || !password) {
            alert("Username and password cannot be empty.");
            return;
        }

        // Attempt to login
        try {
            const loginResponse = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const loginData = await loginResponse.json();
            console.log("Login response:", loginData);

            if (loginResponse.status === 200) {
                // Login successful
                publicKey = loginData.public_key;
                const encryptedPrivateKey = loginData.encrypted_private_key;
                console.log("Encrypted Private Key received:", encryptedPrivateKey);

                if (encryptedPrivateKey) {
                    // Decrypt the private key using the password
                    const decryptedPrivateKey = decryptPrivateKey(encryptedPrivateKey, password);
                    console.log("Decrypted Private Key:", decryptedPrivateKey);
                    if (!decryptedPrivateKey) {
                        showError("Failed to decrypt private key.");
                        return;
                    }
                    privateKey = decryptedPrivateKey;
                } else {
                    showError("No encrypted private key found. Please register again.");
                    return;
                }

                // After successful login, initialize the app
                initializeApp();
                registerUserWithSocket();
            } else if (loginResponse.status === 404) {
                // User does not exist, attempt to register
                registerUser(username, password);
            } else {
                // Other login errors
                showError(loginData.error || "Login failed.");
            }
        } catch (error) {
            console.error("Error during login:", error);
            showError("An error occurred during login.");
        }
    }

    // Register User Function
    function registerUser(username, password) {
        // Generate RSA key pair
        const rsa = new JSEncrypt({ default_key_size: 2048 });
        rsa.getKey();
        privateKey = rsa.getPrivateKey();
        publicKey = rsa.getPublicKey();
        console.log("Generated Public Key:", publicKey);
        console.log("Generated Private Key:", privateKey);

        // Encrypt the private key with the password
        const encryptedPrivateKey = encryptPrivateKey(privateKey, password);
        console.log("Encrypted Private Key during registration:", encryptedPrivateKey);

        if (!encryptedPrivateKey) {
            showError("Failed to encrypt private key.");
            return;
        }

        // Register the user with the server
        fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                password,
                public_key: publicKey,
                encrypted_private_key: encryptedPrivateKey,
            }),
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(({ status, body }) => {
            if (status === 201) {
                // Registration successful
                initializeApp();
                registerUserWithSocket();
            } else {
                // Registration failed
                showError(body.error || "Registration failed.");
            }
        })
        .catch(error => {
            console.error("Error during registration:", error);
            showError("An error occurred during registration.");
        });
    }

    // Register User with Socket.IO
    function registerUserWithSocket() {
        console.log("Registering user with Socket.IO");
        socket.emit("user_join", { username, public_key: publicKey });
        sidebar.style.display = "block";
        chatContainer.style.display = "none";
    }

    // Receive Chat Messages
    socket.on("chat", (data) => {
        console.log("Received chat event:", data);
        const sender = data.username;
        const encryptedMessage = data.message;
        const group = data.group || null;

        let decryptedMessage = decryptMessage(encryptedMessage);

        if (group && group === currentChat && isGroupChat) {
            appendMessage(`${sender} to ${group}: ${decryptedMessage}`);
        } else if (!group && sender === currentChat && !isGroupChat) {
            appendMessage(`${sender}: ${decryptedMessage}`);
        }
    });

    socket.on("connect", () => {
        console.log("Connected to server.");
    });

    socket.on("disconnect", () => {
        console.log("Disconnected from server.");
    });

});