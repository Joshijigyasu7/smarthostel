<!DOCTYPE html>
<html>
<head>
  <title>Wallet Test</title>
</head>
<body>

<h2>MetaMask Connect Test</h2>
<button id="connect">Connect Wallet</button>
<p id="status"></p>

<script>
document.getElementById("connect").onclick = async () => {
  if (typeof window.ethereum === "undefined") {
    document.getElementById("status").innerText =
      "MetaMask not found";
    return;
  }

  try {
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts"
    });

    document.getElementById("status").innerText =
      "Connected: " + accounts[0];

  } catch (error) {
    document.getElementById("status").innerText =
      "User rejected or error";
    console.error(error);
  }
};
</script>

</body>
</html>
