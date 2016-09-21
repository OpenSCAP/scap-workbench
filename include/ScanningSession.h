/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#ifndef SCAP_WORKBENCH_SCANNING_SESSION_H_
#define SCAP_WORKBENCH_SCANNING_SESSION_H_

#include "ForwardDecls.h"

#include <QTemporaryFile>
#include <QSet>
#include <QDir>
#include <map>

extern "C"
{
#include <xccdf_benchmark.h>
}

/**
 * @brief Encapsulates xccdf_session, tailoring and profile selection
 */
class ScanningSession
{
    public:
        ScanningSession();
        ~ScanningSession();

        /**
         * @brief Sets whether openscap validation should be skipped when loading
         */
        void setSkipValid(bool skipValid);

        /**
         * @brief Retrieves the internal xccdf_session structure
         *
         * @note Use of this method is discouraged.
         */
        struct xccdf_session* getXCCDFSession() const;

        /**
         * @brief Opens a specific file
         *
         * Passed file may be an XCCDF file (any openscap supported version)
         * or source datastream (SDS) file (any openscap supported version)
         */
        void openFile(const QString& path);

        /**
         * @brief Closes currently opened file (if any)
         *
         * @throws Does not throw exceptions!
         */
        void closeFile();

        /**
         * @brief Retrieves full absolute path of the opened file
         */
        QString getOpenedFilePath() const;

        /**
         * @brief A helper method that gets the longest common ancestor dir from a set of paths
         */
        static QDir getCommonAncestorDirectory(const QSet<QString>& paths);

        /**
         * @brief List of all files (paths) necessary to evaluate content that is currently loaded
         *
         * @note This does NOT include the tailoring file, has to be handled separately!
         * Returns XCCDF, OVAL, CPEs, anything that is necessary to evaluate.
         */
        QSet<QString> getOpenedFilesClosure() const;

        static void copyOrReplace(const QString& from, const QString& to);

        /**
         * @brief Saves opened file and its dependencies to given directory
         *
         * @note This method does save the tailoring file if any tailoring has been done
         * @return set of file paths we have saved
         */
        QSet<QString> saveOpenedFilesClosureToDir(const QDir& dir);

        /**
         * @brief Returns true if a file has been opened in this session
         *
         * @note Never throws exceptions!
         */
        bool fileOpened() const;

        /**
         * @brief Returns true if a file is loaded and is a source datastream, false otherwise
         */
        bool isSDS() const;

        /**
         * @brief Sets ID of datastream inside the SDS
         *
         * @par
         * This method will throw an exception if no file is opened or if opened file is
         * not a source datastream.
         */
        void setDatastreamID(const QString& datastreamID);
        QString getDatastreamID() const;

        /**
         * @brief Sets ID of XCCDF component inside the SDS
         *
         * @par
         * This method will throw an exception if no file is opened or if opened file is
         * not a source datastream.
         */
        void setComponentID(const QString& componentID);
        QString getComponentID() const;

        /**
         * @brief Retrieves title of effective benchmark that will be used for evaluation
         *
         * In case just an XCCDF file is loaded the title is of the benchmark in that XCCDF file.
         * In case a SDS is loaded the title of the benchmark in selected datastream and component is returned.
         */
        QString getBenchmarkTitle() const;

        /**
         * @brief Removes all tailoring (including the tailoring loaded from a file!)
         *
         * The result scanning session will scan as if only the input file was loaded.
         */
        void resetTailoring();
        void setTailoringFile(const QString& tailoringFile);
        void setTailoringComponentID(const QString& componentID);

        /**
         * @brief Saves tailoring to given file path
         *
         * @param userFile if true, the path will be kept as a user provided
         * path for the current tailoring file
         *
         * @see getUserTailoringFilePath
         */
        void saveTailoring(const QString& path, bool userFile);

        /**
         * @brief Exports tailoring file to a temporary path and returns the path
         *
         * @par
         * This method ensures that the file resides at the path returned. If no
         * tailoring file has been loaded, this method ensures a new one is created
         * and exported.
         */
        QString getTailoringFilePath();

        /**
         * @brief Returns the path of tailoring file most suitable for user presentation
         *
         * @par
         * This method returns the most friendly path for the user.
         * If a tailoring file has been loaded or saved by user, its path will be returned.
         * If a profile has been tailored but not saved yet, a temporary path is returned.
         * If there is no tailoring, an empty string is returned.
         */
        QString getUserTailoringFilePath();

        /**
         * @brief Generates guide and saves it to supplied path
         */
        void generateGuide(const QString& path);

        /**
         * @brief Exports guide to a temporary path and returns the path
         *
         * If called multiple times the temporary file is overwritten, at most
         * one temporary file will be created by this method. The file is destroyed
         * when ScanningSession is destroyed.
         */
        QString getGuideFilePath();

        /**
         * @brief Returns true if tailoring has been created and is valid
         *
         * @note A tailoring with 0 profiles isn't valid, the method will return false in that case
         * @note Can be caused by user changes or getTailoringFilePath called
         */
        bool hasTailoring() const;

        /**
         * @brief Returns a map of profile IDs that are available for selection
         *
         * IDs are mapped to respective profiles.
         *
         * Changing component ID and/or tailoring does invalidate the map. Available
         * profiles will change if tailoring or benchmark changes.
         *
         * @see setProfile
         */
        std::map<QString, struct xccdf_profile*> getAvailableProfiles();

        /**
         * @brief Sets which profile to use for scanning
         *
         * Will throw an exception if profile selection fails.
         *
         * @see getAvailableProfiles
         */
        void setProfile(const QString& profileID);

        /**
         * @brief Retrieves currently selected profile for scanning
         *
         * @see setProfile
         */
        QString getProfile() const;

        /**
         * @brief Checks whether a profile is selected
         *
         * (default) profile doesn't count as a profile in this method. This method
         * checks whether a profile other than (default) profile is selected.
         */
        bool profileSelected() const;

        /**
         * @brief Checks whether currently selected profile is a tailoring profile
         *
         * Tailoring profile comes from a tailoring file. It can either have ID of
         * a normal profile (thus shadowing it) or a completely different ID.
         *
         * A profile that is not a tailoring profile comes in the input file.
         */
        bool isSelectedProfileTailoring() const;

        /**
         * @brief Reloads the session if needed, datastream split is potentially done again
         *
         * @param forceReload if true, the reload is forced no matter what mSessionDirty is
         *
         * The main purpose of this method is to allow to reload the session when
         * parameters that affect "loading" of the session change. These parameters
         * are mainly datastream ID and component ID.
         *
         * mSessionDirty is automatically set to true whenever crucial parameters of
         * the session change. reloadSession will early out if reload is not necessary.
         */
        void reloadSession(bool forceReload = false) const;

        /**
         * @brief Creates a new profile, makes it inherit current profile
         *
         * @param shadowed if true the new profile will have the same ID
         * @param newIdBase ID of the new profile, only applicable if @a shadowed is false
         * @return created profile (can be passed to TailoringWindow for further tailoring)
         */
        struct xccdf_profile* tailorCurrentProfile(bool shadowed, const QString& newIdBase);

        const struct xccdf_version_info* getXCCDFVersionInfo();

    private:
        struct xccdf_benchmark* getXCCDFInputBenchmark();
        void ensureTailoringExists();

        /// This is our central point of interaction with openscap
        struct xccdf_session* mSession;
        /// Our own tailoring that may or may not initially be loaded from a file
        mutable struct xccdf_tailoring* mTailoring;

        /// Temporary file provides auto deletion and a valid temp file path
        QTemporaryFile mTailoringFile;
        /// Temporary file provides auto deletion and a valid temp file path
        QTemporaryFile mGuideFile;

        /// Whether or not validation should be skipped
        bool mSkipValid;

        /// If true, the session will be reloaded
        mutable bool mSessionDirty;
        /// If true, we no longer allow changing tailoring entirely
        /// (loading new file, setting it to load from datastream, ...)
        /// user changes to the tailoring would be lost if we reloaded.
        bool mTailoringUserChanges;

        QString mUserTailoringFile;
        QString mUserTailoringCID;
};

#endif
