/* eslint-disable import/first */
require("dotenv").config();
import {
  BrowserRouter as Router,
  Switch,
  Route,
  Link,
  withRouter,
  useLocation,
  Redirect,
} from "react-router-dom";
import "./App.css";
import "./index.css";
import history from "./history";
import Home from "./HomeView";
import GraphView from "./GraphView";
import ThematicMapView from "./ThematicMapView/index.js";
import AboutPage from "./About/index";
import React, { useReducer } from "react";
import MapView from "./MapView";

/* Initial state of app */
const initialState = {
  location: "",
  map: JSON.parse(sessionStorage.getItem("map")),
  numFacilities: 0,
  showPubchemInfo: false,
  chemicals: [],
  currentChemical: "",
  activeTab: 0,
  errorMessage: "",
  filters: {
    chemical: "all",
    pbt: false,
    carcinogen: false,
    releaseType: "all",
    year: 2019,
  },
};

/* handler for updating state */
const reducer = (state, action) => {
  switch (action.type) {
    case "setFilters":
      const newFilters = Object.assign({}, action.payload);
      return { ...state, filters: newFilters };
    case "setMap":
      sessionStorage.setItem("map", JSON.stringify(action.payload));
      return {
        ...state,
        map: action.payload,
      };
    case "setErrorMessage":
      return { ...state, errorMessage: action.payload };
    default:
      throw new Error();
  }
};

/* individual state setters */
const setFilters = (payload) => ({ type: "setFilters", payload });
const setMap = (payload) => ({ type: "setMap", payload });
const setErrorMessage = (payload) => ({ type: "setErrorMessage", payload });

const Navbar = (props) => {
  // webpage path
  const location = useLocation();

  /* Only shows other paths when a search has been initiated */
  return (
    <div
      className={`navigation ${location.pathname === "/" ? "transparent" : ""}`}
    >
      <div className="logo">
        <Link to="/">VET.</Link>
      </div>
      <ul>
        <li className={location.pathname === "/" ? "active" : ""}>
          <Link to="/">Search</Link>
        </li>
        {props.visible && (
          <>
            <li className={location.pathname === "/map" ? "active" : ""}>
              <Link to="/map">Facility Map</Link>
            </li>
            <li className={location.pathname === "/graphs" ? "active" : ""}>
              <Link to="/graphs">Location Insights</Link>
            </li>
            <li
              className={location.pathname === "/thematicmaps" ? "active" : ""}
            >
              <Link to="/thematicmaps">National Insights</Link>
            </li>
            <li className={location.pathname === "/about" ? "active" : ""}>
              <Link to="/about">About</Link>
            </li>
          </>
        )}
      </ul>
    </div>
  );
};

const App = (props) => {
  /* Use reducer method to update state */
  const [state, dispatch] = useReducer(reducer, initialState);

  /* Error handler when API is down */
  function toggleError() {
    dispatch(setErrorMessage("Server request failed, please try again later."));
    setTimeout(() => {
      dispatch(setErrorMessage(""));
    }, 10000);
  }

  /* The geocoder has completed a successful search */
  function handleSuccess(map) {
    dispatch(setMap(map));
    sessionStorage.removeItem("facilityData");
    history.push("/map");
  }

  return (
    /* Entire app is wrapped by router object. Router handles requests to other pages */
    <Router history={history}>
      <Navbar visible={!!state.map} />
      {state.errorMessage !== "" && (
        <div className="error" onClick={() => dispatch(setErrorMessage(""))}>
          {state.errorMessage}
          <div>x</div>
        </div>
      )}
      <div className="app-container">
        <Switch>
          <Route exact path="/map">
            {/* Map, summary, and state thematic map */}
            <MapView></MapView>
          </Route>
          <Route path="/graphs">
            {/* Top ten graphs, timeline graphs, index graphs */}
            {state.map ? (
              <div className="graph-view">
                <GraphView
                  map={state.map}
                  filters={state.filters}
                  onApiError={toggleError}
                  onFilterChange={(filters) => dispatch(setFilters(filters))}
                ></GraphView>
              </div>
            ) : (
              <Redirect to="/" />
            )}
          </Route>
          <Route path="/thematicmaps">
            {/* county and state-level thematic maps for U.S. */}
            {state.map ? (
              <ThematicMapView
                map={state.map}
                filters={state.filters}
                onApiError={toggleError}
                onFilterChange={(filters) => dispatch(setFilters(filters))}
              ></ThematicMapView>
            ) : (
              <Redirect to="/" />
            )}
          </Route>
          <Route path="/about" component={AboutPage}></Route>
          {/* <Route path="/about"></Route> */}
          <Route path="/">
            {/* home page */}
            <Home onSuccess={handleSuccess} />
          </Route>
        </Switch>
      </div>
    </Router>
  );
};

function Footer() {
  return (
    <div className="footer">
      <ul>
        <li>
          <a href="https://github.com/ejdejesu/ToxicantVisualizer">Github</a>
        </li>
        <li>
          <a href="https://pubchem.ncbi.nlm.nih.gov/">Pubchem</a>
        </li>
        <li>
          <a href="https://www.epa.gov/toxics-release-inventory-tri-program">
            TRI Program
          </a>
        </li>
        {/* <li>
          <Link to="/about">About</Link>
        </li> */}
      </ul>
      <div>
        <div className="copyright">
          &#169; VET was developed in 2020 for the Lab for Health and
          Environmental Information by Evan de Jesus, Adwait Wadekar, Richard
          Moore, and Calvin Brooks
        </div>
      </div>
    </div>
  );
}

export default withRouter(App);
