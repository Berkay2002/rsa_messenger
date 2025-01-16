document.addEventListener("DOMContentLoaded", () => {
    const socket = io();

    const landing = document.getElementById("landing");
    const chat = document.getElementById("chat");
    const joinBtn = document.getElementById("join-btn");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const messageInput = document.getElementById("message");
    const chatMessages = document.getElementById("chat-messages");
    const errorMessage = document.getElementById("error-message");

    let username = "";
    let publicKey = "";
    let privateKey = "";

    joinBtn.addEventListener("click", async () => {
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

            if (loginResponse.status === 200) {
                // Login successful
                publicKey = loginData.public_key;
                const encryptedPrivateKey = loginData.encrypted_private_key;

                if (encryptedPrivateKey) {
                    // Decrypt the private key using the password
                    const decryptedPrivateKey = decryptPrivateKey(encryptedPrivateKey, password);
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

    function registerUser(username, password) {
        // Generate RSA key pair
        const rsa = new JSEncrypt({ default_key_size: 2048 });
        rsa.getKey();
        privateKey = rsa.getPrivateKey();
        publicKey = rsa.getPublicKey();

        // Encrypt the private key with the password
        const encryptedPrivateKey = encryptPrivateKey(privateKey, password);

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
        socket.emit("user_join", { username, public_key: publicKey });
        landing.style.display = "none";
        chat.style.display = "block";
    }

    messageInput.addEventListener("keyup", function (event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        const recipient = username; // For simplicity, sending to self
        if (!message) return;

        // Encrypt the message using recipient's public key
        const encrypted = encryptMessage(message, publicKey);
        socket.emit("new_message", { message: encrypted });

        appendMessage(`Me: ${message}`);
        messageInput.value = "";
    }

    socket.on("chat", (data) => {
        const decryptedMessage = decryptMessage(data.message, privateKey);
        appendMessage(`${data.username}: ${decryptedMessage}`);
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
        return encrypt.encrypt(message);
    }

    function decryptMessage(encryptedMessage, privKey) {
        const decrypt = new JSEncrypt();
        decrypt.setPrivateKey(privKey);
        const decrypted = decrypt.decrypt(encryptedMessage);
        return decrypted ? decrypted : "Decryption failed.";
    }

    function encryptPrivateKey(privateKey, password) {
        // Simple encryption using AES for demonstration.
        // For production, use a stronger encryption method.
        const CryptoJS = CryptoJS || window.CryptoJS;
        const encrypted = CryptoJS.AES.encrypt(privateKey, password).toString();
        return encrypted;
    }

    function decryptPrivateKey(encryptedPrivateKey, password) {
        try {
            const CryptoJS = CryptoJS || window.CryptoJS;
            const bytes = CryptoJS.AES.decrypt(encryptedPrivateKey, password);
            const decrypted = bytes.toString(CryptoJS.enc.Utf8);
            return decrypted || null;
        } catch (e) {
            console.error("Private key decryption failed:", e);
            return null;
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
    }
});