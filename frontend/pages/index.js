export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <div className="bg-white p-10 rounded-2xl shadow-lg text-center max-w-md w-full">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Zoho Project Assistant</h1>
        <p className="text-gray-500 mb-8">Manage your Zoho Projects using natural language</p>
        <a
          href="http://localhost:8000/auth/login"
          className="block w-full bg-blue-600 text-white py-3 px-6 rounded-xl font-semibold hover:bg-blue-700 transition"
        >
          Login with Zoho
        </a>
      </div>
    </div>
  );
}

