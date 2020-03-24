import React, { useRef, useEffect }  from 'react';
import './App.css';
import MyWebChat from './components/MyWebChat'


const App = () => {
  const divRef = useRef(null)
  useEffect(() => {
    divRef.current.scrollIntoView({ behavior: 'smooth' })
  })
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
        <div className="ChatWindow"
          ref={divRef}>
          <MyWebChat ></MyWebChat>
        </div>
      </div>
    </div>
  );
}

export default App;
