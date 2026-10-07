import { useState, useEffect } from "react";

// Uses the deployed backend when VITE_API_URL is set,
// otherwise the local FastAPI server
const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

// Turn a FastAPI error response into readable text
function getErrorMessage(data) {
  if (!data) return "Something went wrong.";

  if (typeof data.detail === "string") return data.detail;

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    const field = first.loc ? first.loc[first.loc.length - 1] : "input";
    return `Invalid ${field}: ${first.msg}`;
  }

  return data.message || "Something went wrong.";
}

function App() {
  const [students, setStudents] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [age, setAge] = useState("");
  const [editingId, setEditingId] = useState(null);

  const [command, setCommand] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  // Load users from FastAPI
  async function loadUsers() {
    try {
      const res = await fetch(`${API_URL}/users`);
      const data = await res.json();
      setStudents(data);
    } catch (error) {
      setResponse("Could not connect to FastAPI.");
    }
  }

  // Load users when the page opens
  useEffect(() => {
    loadUsers();
  }, []);

  // Add or update a student through the backend
  async function handleSubmit(e) {
    e.preventDefault();

    if (!name || !email || !age) {
      alert("Please fill in all fields.");
      return;
    }

    const body = JSON.stringify({
      name,
      email,
      age: Number(age),
    });

    const url =
      editingId !== null
        ? `${API_URL}/users/${editingId}`
        : `${API_URL}/users`;

    const method = editingId !== null ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body,
      });

      const data = await res.json();

      if (!res.ok) {
        setResponse(getErrorMessage(data));
        return;
      }

      setResponse(data.message);
      setEditingId(null);
      setName("");
      setEmail("");
      setAge("");

      await loadUsers();
    } catch (error) {
      setResponse("Could not connect to FastAPI.");
    }
  }

  function handleEdit(student) {
    setName(student.name);
    setEmail(student.email);
    setAge(student.age);
    setEditingId(student.id);
  }

  // Delete a student through the backend
  async function handleDelete(id) {
    if (!window.confirm("Delete this student?")) {
      return;
    }

    try {
      const res = await fetch(`${API_URL}/users/${id}`, {
        method: "DELETE",
      });

      const data = await res.json();

      if (!res.ok) {
        setResponse(getErrorMessage(data));
        return;
      }

      // If the deleted student was being edited, reset the form
      if (editingId === id) {
        setEditingId(null);
        setName("");
        setEmail("");
        setAge("");
      }

      setResponse(data.message);
      await loadUsers();
    } catch (error) {
      setResponse("Could not connect to FastAPI.");
    }
  }

  async function sendCommand() {
    if (!command.trim()) {
      alert("Please enter a command.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/command`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          command: command,
        }),
      });

      const data = await res.json();

      setResponse(
        data.message ||
          (data.detail ? "Request error." : "No message returned.")
      );

      // Refresh the table from the backend
      await loadUsers();

      setCommand("");
    } catch (error) {
      setResponse("Could not connect to FastAPI.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>Student Management</h1>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Student Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="number"
          placeholder="Age"
          value={age}
          onChange={(e) => setAge(e.target.value)}
        />

        <button type="submit">
          {editingId !== null
            ? "Update Student"
            : "Add Student"}
        </button>
      </form>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Age</th>
            <th>Actions</th>
          </tr>
        </thead>

        <tbody>
          {students.map((student) => (
            <tr key={student.id}>
              <td>{student.id}</td>
              <td>{student.name}</td>
              <td>{student.email}</td>
              <td>{student.age}</td>
              <td>
                <button
                  onClick={() => handleEdit(student)}
                >
                  Edit
                </button>

                <button
                  onClick={() => handleDelete(student.id)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {students.length === 0 && (
        <p>No students added yet.</p>
      )}

      <div className="command-box">
        <h2>AI Command</h2>

        <input
          type="text"
          placeholder="Type a command, e.g. Create user Ali, ali@gmail.com, age 22"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !loading) {
              sendCommand();
            }
          }}
        />

        <button onClick={sendCommand} disabled={loading}>
          {loading ? "Working..." : "Send"}
        </button>

        {response && (
          <p className="command-response">{response}</p>
        )}
      </div>
    </div>
  );
}

export default App;