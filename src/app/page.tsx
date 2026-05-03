<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Wallet Landing</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      background-color: #f4f4f4;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }
    header {
      background-color: #333;
      color: white;
      padding: 1rem;
      text-align: center;
    }
    .balance {
      background-color: white;
      padding: 2rem;
      margin: 2rem 0;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      text-align: center;
    }
    .transactions {
      background-color: white;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .buttons {
      display: flex;
      justify-content: center;
      gap: 1rem;
      margin-top: 2rem;
    }
    button {
      padding: 0.75rem 1.5rem;
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    button:hover {
      background-color: #0056b3;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>My Wallet</h1>
    </header>

    <section class="balance">
      <h2>Current Balance</h2>
      <p style="font-size: 2em; color: #28a745; font-weight: bold;">$1,234.56</p>
    </section>

    <section class="transactions">
      <h2>Recent Transactions</h2>
      <ul style="list-style: none; padding: 0;">
        <li style="padding: 0.5rem 0; border-bottom: 1px solid #eee;">
          <strong>Payment to Alice</strong><br />
          <span style="color: #dc3545;">-$50.00</span> · Today 2:30 PM
        </li>
        <li style="padding: 0.5rem 0; border-bottom: 1px solid #eee;">
          <strong>Received from Bob</strong><br />
          <span style="color: #28a745;">+$100.00</span> · Yesterday 4:15 PM
        </li>
        <li style="padding: 0.5rem 0;">
          <strong>Grocery Purchase</strong><br />
          <span style="color: #dc3545;">-$25.50</span> · Jan 28, 2024 10:00 AM
        </li>
      </ul>
    </section>

    <div class="buttons">
      <button onclick="alert('Send functionality would go here')">Send</button>
      <button onclick="alert('Receive functionality would go here')">Receive</button>
    </div>
  </div>
</body>
</html>