/**
 * android_example.kt
 *
 * Example Android 15+ (API 35+) implementation that:
 *  1. Receives a forwarded WhatsApp webhook payload from a backend server.
 *  2. Calls the Python backend REST endpoint to process the message.
 *  3. Displays the conversation (user messages + GPT replies) in a RecyclerView.
 *
 * Prerequisites
 * -------------
 * - A running instance of the Python backend (webhook_listener.py wrapped in Flask).
 * - The backend URL configured in BuildConfig or a local .properties file.
 * - Internet permission in AndroidManifest.xml:
 *     <uses-permission android:name="android.permission.INTERNET" />
 *
 * Minimum SDK: 35 (Android 15)
 * Target SDK:  35+
 *
 * Dependencies (app/build.gradle.kts):
 *   implementation("com.squareup.retrofit2:retrofit:2.11.0")
 *   implementation("com.squareup.retrofit2:converter-gson:2.11.0")
 *   implementation("androidx.security:security-crypto:1.1.0-alpha06")
 *   implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.0")
 *   implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.0")
 */

package com.example.whatsappbusiness

import android.os.Bundle
import android.util.Log
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

/** A single chat bubble shown in the RecyclerView. */
data class ChatMessage(
    val text: String,
    val isFromUser: Boolean,
)

/** Request body sent to the Python backend. */
data class ProcessRequest(val payload: Map<String, Any>)

/** Response body received from the Python backend. */
data class ProcessResponse(
    val status: String,
    val response_text: String?,
    val conversation_id: String?,
    val error: String?,
)

// ---------------------------------------------------------------------------
// Retrofit API interface
// ---------------------------------------------------------------------------

interface WhatsAppBackendApi {
    /**
     * POST /process  — forward the raw webhook payload to the Python backend
     * and receive the GPT-generated reply.
     */
    @POST("process")
    suspend fun processMessage(@Body request: ProcessRequest): ProcessResponse
}

// ---------------------------------------------------------------------------
// Secure credential helper
// ---------------------------------------------------------------------------

/**
 * Stores sensitive configuration (backend URL, API keys) using
 * AndroidX EncryptedSharedPreferences backed by the Android Keystore.
 *
 * Never hard-code credentials in source code.
 */
object SecureCredentials {

    private const val PREFS_NAME = "whatsapp12_secure_prefs"
    private const val KEY_BACKEND_URL = "backend_url"

    fun getBackendUrl(activity: AppCompatActivity): String {
        val masterKey = MasterKey.Builder(activity)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        val prefs = EncryptedSharedPreferences.create(
            activity,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )

        // Return stored URL or fall back to a local dev server default.
        return prefs.getString(KEY_BACKEND_URL, "http://10.0.2.2:8080/") ?: "http://10.0.2.2:8080/"
    }
}

// ---------------------------------------------------------------------------
// ViewModel
// ---------------------------------------------------------------------------

class ChatViewModel : ViewModel() {

    private val _messages = mutableListOf<ChatMessage>()
    val messages: List<ChatMessage> get() = _messages

    private lateinit var api: WhatsAppBackendApi

    fun init(backendUrl: String) {
        api = Retrofit.Builder()
            .baseUrl(backendUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(WhatsAppBackendApi::class.java)
    }

    /**
     * Simulate sending a WhatsApp webhook payload to the Python backend
     * and appending both the user message and the GPT reply to the list.
     *
     * In production this payload would be forwarded from your webhook
     * server; here we construct a minimal example payload for demo purposes.
     */
    fun sendMessage(userText: String, onUpdate: (List<ChatMessage>) -> Unit) {
        _messages.add(ChatMessage(text = userText, isFromUser = true))
        onUpdate(_messages.toList())

        viewModelScope.launch {
            try {
                val simulatedPayload = buildSimulatedPayload(userText)
                val response = api.processMessage(ProcessRequest(simulatedPayload))

                if (response.status == "success" && response.response_text != null) {
                    _messages.add(ChatMessage(text = response.response_text, isFromUser = false))
                } else {
                    val errorText = response.error ?: "Unknown error"
                    _messages.add(ChatMessage(text = "⚠️ $errorText", isFromUser = false))
                }
            } catch (e: Exception) {
                Log.e("ChatViewModel", "Backend call failed", e)
                _messages.add(ChatMessage(text = "⚠️ Could not reach backend: ${e.message}", isFromUser = false))
            }
            onUpdate(_messages.toList())
        }
    }

    /**
     * Build a minimal WhatsApp Cloud API webhook payload for demo/testing.
     * Real deployments receive this payload directly from Meta's servers.
     */
    private fun buildSimulatedPayload(text: String): Map<String, Any> = mapOf(
        "object" to "whatsapp_business_account",
        "entry" to listOf(
            mapOf(
                "id" to "BUSINESS_ACCOUNT_ID",
                "changes" to listOf(
                    mapOf(
                        "value" to mapOf(
                            "messaging_product" to "whatsapp",
                            "metadata" to mapOf(
                                "display_phone_number" to "15550001234",
                                "phone_number_id" to "PHONE_NUMBER_ID",
                            ),
                            "messages" to listOf(
                                mapOf(
                                    "from" to "15559876543",
                                    "id" to "wamid.EXAMPLE",
                                    "timestamp" to (System.currentTimeMillis() / 1000).toString(),
                                    "text" to mapOf("body" to text),
                                    "type" to "text",
                                )
                            ),
                        ),
                        "field" to "messages",
                    )
                ),
            )
        ),
    )
}

// ---------------------------------------------------------------------------
// RecyclerView Adapter
// ---------------------------------------------------------------------------

class ChatAdapter : ListAdapter<ChatMessage, ChatAdapter.MessageViewHolder>(DIFF_CALLBACK) {

    override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): MessageViewHolder {
        val tv = android.widget.TextView(parent.context).apply {
            val dp8 = (8 * resources.displayMetrics.density).toInt()
            setPadding(dp8 * 2, dp8, dp8 * 2, dp8)
            textSize = 16f
        }
        return MessageViewHolder(tv)
    }

    override fun onBindViewHolder(holder: MessageViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class MessageViewHolder(private val tv: android.widget.TextView) :
        RecyclerView.ViewHolder(tv) {

        fun bind(msg: ChatMessage) {
            tv.text = if (msg.isFromUser) "You: ${msg.text}" else "GPT: ${msg.text}"
            tv.setBackgroundColor(
                if (msg.isFromUser) 0xFFDCF8C6.toInt() else 0xFFFFFFFF.toInt()
            )
        }
    }

    companion object {
        private val DIFF_CALLBACK = object : DiffUtil.ItemCallback<ChatMessage>() {
            override fun areItemsTheSame(old: ChatMessage, new: ChatMessage) = old === new
            override fun areContentsTheSame(old: ChatMessage, new: ChatMessage) = old == new
        }
    }
}

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

/**
 * Main Activity — minimal chat UI demonstrating the WhatsApp12 skill.
 *
 * Layout is created programmatically to keep the example self-contained.
 * In a real app, use a proper XML layout with ViewBinding.
 */
class MainActivity : AppCompatActivity() {

    private val viewModel: ChatViewModel by viewModels()
    private lateinit var adapter: ChatAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val backendUrl = SecureCredentials.getBackendUrl(this)
        viewModel.init(backendUrl)

        // Build a simple vertical layout programmatically
        val rootLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
        }

        // RecyclerView for messages
        val recyclerView = RecyclerView(this).apply {
            layoutManager = LinearLayoutManager(context).also { it.stackFromEnd = true }
            adapter = ChatAdapter().also { this@MainActivity.adapter = it }
        }
        rootLayout.addView(
            recyclerView,
            android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f,
            ),
        )

        // Input row
        val inputRow = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
        }
        val editText = android.widget.EditText(this).apply {
            hint = "Type a message…"
        }
        val sendButton = android.widget.Button(this).apply { text = "Send" }

        inputRow.addView(
            editText,
            android.widget.LinearLayout.LayoutParams(0, android.widget.LinearLayout.LayoutParams.WRAP_CONTENT, 1f),
        )
        inputRow.addView(sendButton)
        rootLayout.addView(inputRow)

        setContentView(rootLayout)

        sendButton.setOnClickListener {
            val text = editText.text.toString().trim()
            if (text.isNotEmpty()) {
                editText.text.clear()
                viewModel.sendMessage(text) { messages ->
                    adapter.submitList(messages.toList())
                    recyclerView.scrollToPosition(messages.size - 1)
                }
            }
        }
    }
}
