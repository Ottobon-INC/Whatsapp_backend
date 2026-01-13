# Sakhi WhatsApp Chatbot - Capabilities Report

This document allows us to track what we have built so far for the Sakhi (JanmaSethu) WhatsApp Chatbot.

## 🌟 Project Overview
Sakhi is an intelligent, supportive AI companion designed to guide users through their journey of **fertility, pregnancy, and parenthood**. It acts as a "judgment-free friend" backed by doctor-approved medical wisdom.

## 🚀 Key Functional Capabilities

### 1. Intelligent Conversational Support
*   **Dual-Brain Architecture**: We use a smart combination of models to answer questions accurately and cost-effectively.
    *   **Small Talk**: Handled instantly for natural flow (Greetings, "How are you?").
    *   **Medical Queries**: Uses advanced AI (including GPT-4) to provide detailed, empathetic answers.
*   **Medical Knowledge Base (RAG)**: The bot doesn't just guess; it "looks up" information from a trusted medical database before answering, ensuring accuracy.
*   **Multilingual**: Capable of detecting the user's language and carrying out the conversation in that same language.

### 2. User Onboarding & Personalization
*   **First-Time Experience**: When a new user says "Hi", the bot gently collects their **Name**, **Gender**, and **Location**.
*   **Profile Management**: Remembers user details to personalize conversations (e.g., using their name).
*   **Welcome Kit**: Sends a friendly introduction image (`Sakhi_intro.png`) and sets the tone as a safe, supportive space.

### 3. Dedicated "Lead Generation" Flow
*   **Command**: `/newlead`
*   **Purpose**: Allows clinic staff or partners to quickly register new patient inquiries directly within the chat.
*   **Step-by-Step Collection**: The bot interviews the user to collect:
    1.  Patient Name
    2.  Phone Number
    3.  Age
    4.  Gender
    5.  Health Concern/Problem
*   **Database Integration**: Automatically saves these leads into the secure database for the clinic to follow up.

### 4. Safety & Guardrails
*   **Stay-on-Topic**: The bot allows us to maintain focus. It politely declines to discuss irrelevant topics like **Sports, Politics, or Movies** and steers the conversation back to health and well-being.
*   **Emotional Support Detection**: It can detect if a user is feeling stressed or anxious and provides comforting, empathetic responses rather than just cold medical facts.
*   **Clean Responses**: Automatically filters out robotic phrases like "As an AI language model" to keep the conversation feeling human.

### 5. Rich Media Features
*   **Multimedia Support**: The bot can send:
    *   **Infographics**: Visual explanations for complex topics.
    *   **YouTube Links**: Helpful videos found in our knowledge base.

## 🛠️ Technical Highlights (Simplified)
*   **Smart Routing**: A gateway decides if a question is simple or complex and routes it to the right AI model.
*   **State Management**: The bot remembers where you are in a flow (e.g., if you are halfway through adding a lead, it won't forget).
*   **Database**: robust storage for user profiles, chat history, and leads (Supabase).
