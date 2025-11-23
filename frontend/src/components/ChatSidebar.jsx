import React from 'react';

export default function ChatSidebar({
  sessions = [],
  activeChatId,
  onNewChat,
  onSelectChat
}) {
  return (
    <aside className="w-72 bg-white border-r flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">ChatFinance</h2>
          <div className="text-xs text-gray-500">Your conversations</div>
        </div>

        <button
          onClick={onNewChat}
          className="px-3 py-1 bg-purple-600 text-white rounded-md text-sm hover:bg-purple-700 transition"
        >
          + New
        </button>
      </div>

      {/* Sessions */}
      <div className="p-3 flex-1 overflow-auto">
        {sessions.length === 0 && (
          <div className="text-sm text-gray-500 p-3">No chats yet — create one.</div>
        )}

        <ul className="space-y-2">
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => onSelectChat(s)}
                className={`w-full text-left p-3 rounded-lg transition-colors flex justify-between items-start ${
                  activeChatId === s.id
                    ? 'bg-purple-50 border border-purple-200'
                    : 'hover:bg-gray-100'
                }`}
              >
                <div className="flex-1 overflow-hidden">
                  <div
                    className={`text-sm font-medium truncate ${
                      activeChatId === s.id ? 'text-purple-700' : 'text-gray-900'
                    }`}
                  >
                    {s.title || `Chat ${s.id}`}
                  </div>

                  <div className="text-xs text-gray-500 mt-1 truncate">
                    {s.last_message_preview
                      ? s.last_message_preview.slice(0, 40)
                      : '—'}
                  </div>
                </div>

                <div className="ml-2 text-[10px] text-gray-400 whitespace-nowrap">
                  {new Date(s.updated_at || s.created_at).toLocaleDateString()}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Footer */}
      <div className="p-3 border-t text-xs text-gray-500">
        <div>GHCI-Compliant: No external AI</div>
      </div>
    </aside>
  );
}
