from flask import Flask, render_template_string, request, redirect, url_for, flash
import pandas as pd

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flashing messages

# Example registered voters data
registered_voters = pd.DataFrame({
    'name': ['Alice Johnson', 'Bob Smith', 'Carol Davis'],
    'ssn': ['123-45-6789', '987-65-4321', '555-55-5555']
})

# This will hold the ballots as they're submitted
ballots = pd.DataFrame(columns=['name', 'ssn'])

# HTML Template
template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
        }

        h1 {
            text-align: center;
        }

        table {
            width: 80%;
            margin: 20px auto;
            border-collapse: collapse;
        }

        th, td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: left;
        }

        th {
            background-color: #f4f4f4;
        }

        .error {
            color: red;
            text-align: center;
        }

        .success {
            color: green;
            text-align: center;
        }

        form {
            width: 50%;
            margin: 20px auto;
            padding: 20px;
            border: 1px solid #ddd;
            background-color: #f9f9f9;
        }

        label {
            display: block;
            margin-bottom: 5px;
        }

        input[type="text"], input[type="submit"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
        }
    </style>
    <title>Ballot Submission</title>
</head>
<body>
    <h1>Submit Your Ballot</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <p class="{{ category }}">{{ message }}</p>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form action="{{ url_for('submit_ballot') }}" method="POST">
        <label for="name">Name</label>
        <input type="text" id="name" name="name" required>

        <label for="ssn">SSN</label>
        <input type="text" id="ssn" name="ssn" required>

        <input type="submit" value="Submit Ballot">
    </form>

    <h2>Submitted Ballots</h2>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>SSN</th>
            </tr>
        </thead>
        <tbody>
            {% for ballot in ballots %}
            <tr>
                <td>{{ ballot['name'] }}</td>
                <td>{{ ballot['ssn'] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(template, ballots=ballots.to_dict(orient='records'))

@app.route('/submit', methods=['POST'])
def submit_ballot():
    name = request.form['name']
    ssn = request.form['ssn']

    # Check if the SSN is registered
    if ssn not in registered_voters['ssn'].values:
        flash('Error: SSN is not registered.', 'error')
        return redirect(url_for('index'))

    # Check for duplicate ballot submission
    if ssn in ballots['ssn'].values:
        flash('Error: Duplicate ballot submission detected.', 'error')
        return redirect(url_for('index'))

    # If all checks pass, add the ballot
    global ballots
    ballots = ballots.append({'name': name, 'ssn': ssn}, ignore_index=True)
    flash('Ballot submitted successfully!', 'success')

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
