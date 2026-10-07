import { useState } from "react";

function App() {
  const [students, setStudents] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [age, setAge] = useState("");
  const [editingId, setEditingId] = useState(null);

  function handleSubmit(e) {
    e.preventDefault();

    if (!name || !email || !age) {
      alert("Please fill in all fields.");
      return;
    }

    if (editingId !== null) {
      setStudents(
        students.map((student) =>
          student.id === editingId
            ? { ...student, name, email, age }
            : student
        )
      );

      setEditingId(null);
    } else {
      const newStudent = {
        id: Date.now(),
        name,
        email,
        age,
      };

      setStudents([...students, newStudent]);
    }

    setName("");
    setEmail("");
    setAge("");
  }

  function handleEdit(student) {
    setName(student.name);
    setEmail(student.email);
    setAge(student.age);
    setEditingId(student.id);
  }

  function handleDelete(id) {
    setStudents(students.filter((student) => student.id !== id));
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
          {editingId !== null ? "Update Student" : "Add Student"}
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
          {students.map((student, index) => (
            <tr key={student.id}>
              <td>{index + 1}</td>
              <td>{student.name}</td>
              <td>{student.email}</td>
              <td>{student.age}</td>
              <td>
                <button onClick={() => handleEdit(student)}>
                  Edit
                </button>

                <button onClick={() => handleDelete(student.id)}>
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
    </div>
  );
}

export default App;