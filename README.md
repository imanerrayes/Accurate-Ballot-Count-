# Accurate-Ballot-Count-
# Ballot Submission Dashboard

This project sets up a simple dashboard for submitting and tracking ballots. The dashboard is built using Python and Flask, ensuring that only registered voters can submit ballots and that no duplicate ballots are counted.

## Features
- **Ballot Submission Form**: Users can submit their ballots by entering their name and SSN.
- **Duplicate Check**: The application checks for duplicate SSN entries to ensure that each voter can only submit one ballot.
- **SSN Validation**: The application checks that the SSN provided matches a registered voter.
- **Real-Time Feedback**: The application provides real-time feedback for successful submissions or errors.

## Setup

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/ballot-dashboard.git
    cd ballot-dashboard
    ```

2. Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the dependencies:
    ```bash
    pip install flask pandas
    ```

4. Run the application:
    ```bash
    python ballot_dashboard.py
    ```

5. Open a web browser and go to `http://127.0.0.1:5000/` to view and use the dashboard.

## Usage
- **Submit a Ballot**: Enter your name and SSN in the form and click "Submit Ballot".
- **View Submitted Ballots**: Scroll down to see the list of all successfully submitted ballots.
- **Error Handling**: If you try to submit a ballot with an unregistered SSN or a duplicate SSN, you will see an error message.

## Example Data

The application includes example data for registered voters:
```plaintext
Name: Alice Johnson, SSN: 123-45-6789
Name: Bob Smith, SSN: 987-65-4321
Name: Carol Davis, SSN: 555-55-5555
