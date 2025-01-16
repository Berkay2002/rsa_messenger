// filepath: /c:/Users/berka/Masters/TNM031/rsa_messenger/static/js/main.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();

    const landing = document.getElementById("landing");
    const chat = document.getElementById("chat");
    const joinBtn = document.getElementById("join-btn");
    const usernameInput = document.getElementById("username");
    const messageInput = document.getElementById("message");
    const chatMessages = document.getElementById("chat-messages");

    let username = "";
    let publicKey = "";
    let privateKey = "";

    joinBtn.addEventListener("click", async () => {
        username = usernameInput.value.trim();
        if (!username) {
            alert("Username cannot be empty.");
            return;
        }

        // Fetch public key from the server
        try {
            const response = await fetch(`/get_public_key?username=${username}`);
            const data = await response.json();
            if (response.status === 200) {
                publicKey = data.public_key;
            } else {
                alert(data.error);
                return;
            }
        } catch (error) {
            console.error("Error fetching public key:", error);
            alert("Failed to connect to the server.");
            return;
        }

        // Generate RSA key pair
        const rsa = new JSEncrypt({ default_key_size: 2048 });
        rsa.getKey();
        privateKey = rsa.getPrivateKey();
        publicKey = rsa.getPublicKey();

        // Register the user with the server
        socket.emit("user_join", { username, public_key: publicKey });

        landing.style.display = "none";
        chat.style.display = "block";
    });

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
});