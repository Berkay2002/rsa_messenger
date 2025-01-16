document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM fully loaded and parsed");

    const socket = io();

    const landing = document.getElementById("landing");
    const chat = document.getElementById("chat");
    const joinBtn = document.getElementById("join-btn");
    const sendBtn = document.getElementById("send-btn");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const recipientInput = document.getElementById("recipient");
    const messageInput = document.getElementById("message");
    const chatMessages = document.getElementById("chat-messages");
    const errorMessage = document.getElementById("error-message");

    let username = "";
    let publicKey = "";
    let privateKey = "";

    joinBtn.addEventListener("click", async () => {
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
    });

    sendBtn.addEventListener("click", () => {
        sendMessage();
    });

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

    function registerUserWithSocket() {
        console.log("Registering user with Socket.IO");
        socket.emit("user_join", { username, public_key: publicKey });
        landing.style.display = "none";
        chat.style.display = "block";
    }

    sendBtn.addEventListener("click", () => {
        sendMessage();
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        const recipient = recipientInput.value.trim(); // Get recipient from input

        if (!recipient) {
            alert("Please enter a recipient username.");
            return;
        }
        if (!message) {
            alert("Message cannot be empty.");
            return;
        }

        // Fetch recipient's public key
        fetch(`/get_public_key?username=${encodeURIComponent(recipient)}`)
            .then(response => response.json())
            .then(data => {
                if (data.public_key) {
                    // Encrypt the message using recipient's public key
                    const encrypted = encryptMessage(message, data.public_key);
                    console.log("Encrypted Message:", encrypted);

                    // Emit the message with recipient info
                    socket.emit("new_message", { recipient, message: encrypted });

                    appendMessage(`Me to ${recipient}: ${message}`);
                    messageInput.value = "";
                } else {
                    showError(`Public key for ${recipient} not found.`);
                }
            })
            .catch(error => {
                console.error("Error fetching public key:", error);
                showError("Failed to fetch recipient's public key.");
            });
    }

    socket.on("chat", (data) => {
        console.log("Received chat event:", data);
        const sender = data.username;
        const encryptedMessage = data.message;

        // Only process messages sent to this user
        // The message was encrypted with this user's public key
        const decryptedMessage = decryptMessage(encryptedMessage, privateKey);
        if (decryptedMessage !== "Decryption failed.") {
            appendMessage(`${sender}: ${decryptedMessage}`);
        } else {
            appendMessage(`${sender}: Decryption failed.`);
        }
    });

    socket.on("connect", () => {
        console.log("Connected to server.");
    });

    socket.on("disconnect", () => {
        console.log("Disconnected from server.");
    });

    function appendMessage(message) {
        const li = document.createElement("li");
        li.textContent = message;
        chatMessages.appendChild(li);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function encryptMessage(message, pubKey) {
        const encrypt = new JSEncrypt();
        encrypt.setPublicKey(pubKey);
        const encryptedMessage = encrypt.encrypt(message);
        console.log("Message encrypted with public key:", encryptedMessage);
        return encryptedMessage;
    }

    function decryptMessage(encryptedMessage, privKey) {
        const decrypt = new JSEncrypt();
        decrypt.setPrivateKey(privKey);
        const decrypted = decrypt.decrypt(encryptedMessage);
        if (decrypted) {
            console.log("Message decrypted successfully:", decrypted);
            return decrypted;
        } else {
            console.error("Decryption failed for message:", encryptedMessage);
            return "Decryption failed.";
        }
    }

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

    function showError(message) {
        console.error("Error:", message);
        errorMessage.textContent = message;
    }
});