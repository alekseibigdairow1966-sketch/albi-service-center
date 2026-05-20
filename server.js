require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Конфигурация Telegram
const BOT_TOKEN = process.env.BOT_TOKEN || '8523648387:AAEhmf30rvtXjv-40lxscm3gItFboNwhnbA';
const CHAT_ID = process.env.CHAT_ID || ''; // Ваш ID будет определён автоматически
const BOT_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Хранилище заявок в памяти
const leads = [];

// Форматирование названия устройства
const deviceNames = {
    phone: 'Смартфон',
    laptop: 'Ноутбук',
    pc: 'Компьютер',
    tablet: 'Планшет',
    watch: 'Умные часы',
    other: 'Другое'
};

// Отправка сообщения в Telegram
async function sendTelegramMessage(chatId, text, options = {}) {
    try {
        const response = await axios.post(`${BOT_API}/sendMessage`, {
            chat_id: chatId,
            text: text,
            parse_mode: 'HTML',
            ...options
        });
        return response.data;
    } catch (error) {
        console.error('Telegram API Error:', error.response?.data || error.message);
        throw error;
    }
}

// Отправка заявки в Telegram
async function sendLeadToTelegram(lead) {
    const deviceName = deviceNames[lead.device] || lead.device;
    const date = new Date().toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });

    const message = `
<b>🔔 Новая заявка с сайта АЛБИ</b>

<b>👤 Имя:</b> ${lead.name}
<b>📱 Телефон:</b> <a href="tel:${lead.phone}">${lead.phone}</a>
<b>🔧 Устройство:</b> ${deviceName}
<b>📝 Проблема:</b> ${lead.problem || 'Не указана'}
<b>📅 Дата:</b> ${date}
<b>№ заявки:</b> #${lead.id}
    `.trim();

    // Если CHAT_ID ещё не установлен — отправляем во все чаты, где есть бот
    const targetChatId = CHAT_ID || '@albi_service_semey';

    try {
        const result = await sendTelegramMessage(targetChatId, message, {
            reply_markup: {
                inline_keyboard: [
                    [
                        { text: '✅ Принято', callback_data: `accept_${lead.id}` },
                        { text: '📞 Позвонить', callback_data: `call_${lead.id}` },
                        { text: '✉️ Ответить', callback_data: `reply_${lead.id}` }
                    ],
                    [
                        { text: '📋 Копировать телефон', callback_data: `copy_${lead.id}` }
                    ]
                ]
            }
        });

        // Сохраняем ID сообщения для последующих ответов
        lead.messageId = result.message_id;
        lead.chatId = targetChatId;
        
        console.log(`✅ Заявка #${lead.id} отправлена в Telegram`);
        return true;
    } catch (error) {
        console.error('❌ Ошибка отправки в Telegram:', error.message);
        return false;
    }
}

// Обработка callback от inline-кнопок
async function handleCallback(callbackQuery) {
    const data = callbackQuery.data;
    const chatId = callbackQuery.message.chat.id;
    const leadId = parseInt(data.split('_')[1]);
    const action = data.split('_')[0];
    
    const lead = leads.find(l => l.id === leadId);
    if (!lead) return;

    let responseText = '';
    let showAlert = true;

    switch (action) {
        case 'accept':
            responseText = `✅ Заявка #${leadId} принята. Свяжитесь с клиентом: ${lead.phone}`;
            break;
        case 'call':
            responseText = `📞 Позвоните клиенту: ${lead.phone}\nИмя: ${lead.name}`;
            break;
        case 'copy':
            responseText = `📋 Телефон скопирован: ${lead.phone}`;
            break;
        case 'reply':
            // Для ответа — бот запросит текст
            responseText = `✉️ Чтобы ответить клиенту, отправьте текст в чат с префиксом /reply${leadId} текст_ответа`;
            break;
    }

    await axios.post(`${BOT_API}/answerCallbackQuery`, {
        callback_query_id: callbackQuery.id,
        text: responseText,
        show_alert: showAlert
    });
}

// Обработка входящих сообщений от бота (команды)
async function handleMessage(message) {
    const text = message.text || '';
    const chatId = message.chat.id;

    // Определяем CHAT_ID при первом сообщении
    if (!CHAT_ID && message.chat.type === 'private') {
        process.env.CHAT_ID = chatId;
        console.log(`📌 Ваш Chat ID определён: ${chatId}`);
    }

    // Обработка команды /reply<id>
    if (text.startsWith('/reply')) {
        const match = text.match(/^\/reply(\d+)\s+(.*)/);
        if (match) {
            const leadId = parseInt(match[1]);
            const replyText = match[2];
            const lead = leads.find(l => l.id === leadId);
            
            if (lead) {
                // Отправляем ответ клиенту (если бот может ему написать)
                // Для этого клиент должен быть в боте или иметь Telegram username
                await sendTelegramMessage(chatId, `✉️ Ответ для клиента ${lead.name}:\n${replyText}\n\n💡 Для отправки клиенту — свяжитесь через WhatsApp: https://wa.me/${lead.phone.replace(/\D/g, '')}`);
            }
        }
    }

    // Команда /start
    if (text === '/start') {
        await sendTelegramMessage(chatId, `
<b>🤖 Бот Сервисного центра АЛБИ</b>

Вы будете получать уведомления о новых заявках с сайта.

<b>Доступные команды:</b>
/start — начать
/stats — статистика заявок
/help — помощь
        `.trim());
    }

    // Команда /stats
    if (text === '/stats') {
        const today = new Date().toDateString();
        const todayLeads = leads.filter(l => new Date(l.createdAt).toDateString() === today);
        await sendTelegramMessage(chatId, `
<b>📊 Статистика заявок</b>

Всего заявок: ${leads.length}
Сегодня: ${todayLeads.length}
        `.trim());
    }
}

// Polling — получение обновлений от Telegram
let lastUpdateId = 0;

async function getUpdates() {
    try {
        const response = await axios.get(`${BOT_API}/getUpdates`, {
            params: { offset: lastUpdateId + 1, timeout: 30 }
        });

        const updates = response.data.result;
        for (const update of updates) {
            lastUpdateId = update.update_id;

            if (update.callback_query) {
                await handleCallback(update.callback_query);
            } else if (update.message) {
                await handleMessage(update.message);
            }
        }
    } catch (error) {
        console.error('Polling error:', error.message);
    }
}

// Запуск polling
setInterval(getUpdates, 1000);
getUpdates(); // Первый запуск сразу

// === API ROUTES ===

// Получение заявки с формы
app.post('/api/lead', async (req, res) => {
    try {
        const { name, phone, device, message } = req.body;

        // Валидация
        if (!name || !phone) {
            return res.status(400).json({ error: 'Имя и телефон обязательны' });
        }

        const lead = {
            id: leads.length + 1,
            name: name.trim(),
            phone: phone.trim(),
            device: device || 'Не указано',
            problem: message || 'Не указана',
            createdAt: new Date().toISOString()
        };

        leads.push(lead);
        
        // Отправляем в Telegram
        const sent = await sendLeadToTelegram(lead);

        if (sent) {
            res.json({ success: true, message: 'Заявка отправлена' });
        } else {
            res.status(500).json({ error: 'Ошибка отправки уведомления' });
        }
    } catch (error) {
        console.error('Lead error:', error);
        res.status(500).json({ error: 'Внутренняя ошибка сервера' });
    }
});

// Получение статистики
app.get('/api/stats', (req, res) => {
    res.json({
        total: leads.length,
        today: leads.filter(l => new Date(l.createdAt).toDateString() === new Date().toDateString()).length,
        leads: leads.slice(-10) // Последние 10
    });
});

// Запуск сервера
app.listen(PORT, () => {
    console.log('========================================');
    console.log('🚀 Сервер АЛБИ запущен');
    console.log(`📍 Порт: ${PORT}`);
    console.log(`🤖 Бот: @albi_service_semey`);
    console.log('========================================');
    console.log(`Откройте http://localhost:${PORT} для просмотра сайта`);
});
