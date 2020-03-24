import React from 'react';
import logo from './logo.svg';
import './App.css';
import MyWebChat from './components/MyWebChat'


function App() {
  return (
    <div className="App">
      <header className="App-header">
        <div className="Item">
            <p style={{fontWeight : 'bold'}}>Realherobot</p>
            <p>Open source initiave of some Microsoft employees, who want to bring you the latest statistics in Corona Virus occurence</p>
        </div>
        <div className="Item">

        </div>

      </header>
      <div className="AppFrame">
        <div className="ChatWindow">
          <MyWebChat ></MyWebChat>
        </div>
      </div>
    </div>
  );
}

export default App;
